#!/usr/bin/python
#coding=utf-8

import math
import sys
import json
import os
import collections
import numpy as np
import tensorflow as tf
from tensorflow.python.framework import dtypes
#from dataset import DataSet
from dataset_eng import DataSet

# 产生随机变量，符合 normal 分布
# 传递 shape 就可以返回weight和bias的变量
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)    
    return tf.Variable(initial)

def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)

# 定义2维的 convolutional 图层
def conv2d(x, W):
    # stride [1, x_movement, y_movement, 1]
    # Must have strides[0] = strides[3] = 1
    # strides 就是跨多大步抽取信息
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')        

# 定义 pooling 图层
def max_pool_2x2(x):
    # stride [1, x_movement, y_movement, 1]
    # 用pooling对付跨步大丢失信息问题
    return tf.nn.max_pool(x, ksize=[1,2,2,1], strides=[1,2,2,1], padding='SAME')    

# 定义 pooling 图层
def max_pool_5x5(x):
    # stride [1, x_movement, y_movement, 1]
    # 用pooling对付跨步大丢失信息问题
    return tf.nn.max_pool(x, ksize=[1,5,5,1], strides=[1,5,5,1], padding='SAME')    

#输入
Target_Accuracy = 0.75
xs = tf.placeholder(tf.float32, [None, 1200])
#todo
ys = tf.placeholder(tf.float32, shape=[None, DataSet.AlphaBeta_num])
keep_prob = tf.placeholder(tf.float32)
x_image = tf.reshape(xs, [-1, 40, 30, 1])

## 1. conv1 layer ##
#  把x_image的厚度1加厚变成了32
W_conv1 = weight_variable([5, 5, 1, 32])                 # patch 5x5, in size 1, out size 32
b_conv1 = bias_variable([32])
# 构建第一个convolutional层，外面再加一个非线性化的处理relu
h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)            # output size 40x30x32
# 经过pooling后，长宽缩小为20x15
h_pool1 = max_pool_2x2(h_conv1)                                     # output size 20x15x32

## 2. conv2 layer ##
# 把厚度32加厚变成了64
W_conv2 = weight_variable([5, 5, 32, 64])                 # patch 5x5, in size 32, out size 64
b_conv2 = bias_variable([64])
# 构建第二个convolutional层
h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)            # output size 20x15x64
# 经过pooling后，长宽缩小为7x7
h_pool2 = max_pool_5x5(h_conv2)                                     # output size 4x3x64

## 3. func1 layer ##
# 飞的更高变成1024
W_fc1 = weight_variable([4*3*64, 1024])
b_fc1 = bias_variable([1024])
# [n_samples, 7, 7, 64] ->> [n_samples, 7*7*64]
# 把pooling后的结果变平
h_pool2_flat = tf.reshape(h_pool2, [-1, 4*3*64])
h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1) + b_fc1)
h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

## 4. func2 layer ##
# 最后一层，输入1024，输出size 10，用 softmax 计算概率进行分类的处理
W_fc2 = weight_variable([1024, DataSet.AlphaBeta_num])
b_fc2 = bias_variable([DataSet.AlphaBeta_num])
prediction = tf.nn.softmax(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)


# the error between prediction and real data
cross_entropy = tf.reduce_mean(-tf.reduce_sum(ys * tf.log(prediction),
                                              reduction_indices=[1]))       # loss
train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)



def train():
    #训练数据
    data_train, label_train = DataSet.data_from_text(DataSet.Train_File,DataSet.AlphaBeta_num*50)
    train = DataSet(data_train, label_train, dtype=dtypes.float32)
    data_test, label_test = DataSet.data_from_text(DataSet.Test_File,DataSet.AlphaBeta_num*5)
    test = DataSet(data_test, label_test, dtype=dtypes.float32)
    DataSetsx = collections.namedtuple('DataSetsx', ['train', 'test'])
    Data = DataSetsx(train=train, test=test)

    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()
        for i in range(50000):                                  #训练阶段，迭代50000次
            batch_X, batch_Y =Data.train.next_batch(100)
            sess.run(train_step, feed_dict={xs: batch_X, ys: batch_Y, keep_prob: 0.5})
            accu = 0
            if(i%100==0):                                        #每训练100次，测试一次
                v_xs = Data.test.images
                v_ys = Data.test.labels
                y_pre = sess.run(prediction, feed_dict={xs: v_xs, keep_prob: 1})
                correct_prediction = tf.equal(tf.argmax(y_pre,1), tf.argmax(v_ys,1))
                accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
                accu = sess.run(accuracy, feed_dict={xs: v_xs, ys: v_ys, keep_prob: 1})
                print ("accuracy:", accu)
            if(accu>Target_Accuracy):
                break
        saver.save(sess, "./model/cnn.ckpt")

def test(testimg):
    #输入图像
    data_tester, label_tester = DataSet.data_from_img(testimg)
    tester = DataSet(data_tester, label_tester, dtype=dtypes.float32)

    #测试
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()
        saver.restore(sess, "./model/cnn.ckpt")
        accu = sess.run(ys, feed_dict={ys: tester.labels})
        actual = -1
        for i in range(0,DataSet.AlphaBeta_num):
            if accu[0,i]>0:
                actual = i
                break
        predict = [-1,-1,-1]
        pr_mean = [-1,-1,-1]
        v_xs = tester.images
        v_ys = tester.labels
        prdi = sess.run(prediction, feed_dict={xs: v_xs, keep_prob: 1})
        for i in range(0,DataSet.AlphaBeta_num):
            if prdi[0,i]> pr_mean[2]:
                predict[2] = i
                pr_mean[2] = prdi[0,i]
            if prdi[0,i]> pr_mean[1]:
                predict[2] = predict[1]
                pr_mean[2] = pr_mean[1]
                predict[1] = i
                pr_mean[1] = prdi[0,i]
            if prdi[0,i]> pr_mean[0]:
                predict[1] = predict[0]
                pr_mean[1] = pr_mean[0]
                predict[0] = i
                pr_mean[0] = prdi[0,i]
        ald = pr_mean[0] + pr_mean[1] + pr_mean[2]
        pr_mean[0] = pr_mean[0] / ald
        pr_mean[1] = pr_mean[1] / ald
        pr_mean[2] = pr_mean[2] / ald
        print ("实际输入:", DataSet.AlphaBeta[actual+1])
        print ("预测:", DataSet.AlphaBeta[predict[0]+1],"，概率:", pr_mean[0])
        print ("预测:", DataSet.AlphaBeta[predict[1]+1],"，概率:", pr_mean[1])
        print ("预测:", DataSet.AlphaBeta[predict[2]+1],"，概率:", pr_mean[2])

def predic(input_img):
    data_tester, label_tester = DataSet.data_from_array(input_img)
    tester = DataSet(data_tester, label_tester, dtype=dtypes.float32)
    predict = [-1,-1,-1]
    pr_mean = [-1,-1,-1]
    pr_rtn = ['a','b','c']
    with tf.Session() as sess:
        sess.run(tf.global_variables_initializer())
        saver = tf.train.Saver()
        saver.restore(sess, "./model/cnn.ckpt")
        v_xs = tester.images
        v_ys = tester.labels
        prdi = sess.run(prediction, feed_dict={xs: v_xs, keep_prob: 1})
    for i in range(0,DataSet.AlphaBeta_num):
        if prdi[0,i]> pr_mean[2]:
            predict[2] = i
            pr_mean[2] = prdi[0,i]
        if prdi[0,i]> pr_mean[1]:
            predict[2] = predict[1]
            pr_mean[2] = pr_mean[1]
            predict[1] = i
            pr_mean[1] = prdi[0,i]
        if prdi[0,i]> pr_mean[0]:
            predict[1] = predict[0]
            pr_mean[1] = pr_mean[0]
            predict[0] = i
            pr_mean[0] = prdi[0,i]
    ald = pr_mean[0] + pr_mean[1] + pr_mean[2]
    pr_mean[0] = pr_mean[0] / ald
    pr_mean[1] = pr_mean[1] / ald
    pr_mean[2] = pr_mean[2] / ald
    pr_rtn[0]  = DataSet.AlphaBeta[predict[0]+1]
    pr_rtn[1]  = DataSet.AlphaBeta[predict[1]+1]
    pr_rtn[2]  = DataSet.AlphaBeta[predict[2]+1]

    return pr_mean,pr_rtn

#train()
#test('./Hnd/Tny/Sample007/img007-054.jpg')

#pr_mean,pr_rtn = predic([255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,0,118,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,162,0,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,44,0,255,255,255,0,0,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,51,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,0,32,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,0,8,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,0,17,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,109,0,101,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,239,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,255,255,255,255,255,255,135,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,0,0,15,15,15,9,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,0,0,0,99,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,7,0,0,0,110,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,84,255,255,255,255,255,255,255,255,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,53,255,255,255,255,255,255,255,255,255,255,0,0,0,138,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,52,255,255,255,255,255,255,255,255,255,255,255,250,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,106,255,255,255,255,255,255,255,255,255,255,255,255,255,251,203,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255])
#rtn = '"%s","%s","%s","%s","%s","%s"]' % (str(pr_mean[0]).encode('utf-8'),str(pr_mean[1]).encode('utf-8'),str(pr_mean[2]).encode('utf-8'),pr_rtn[0].encode('utf-8'),pr_rtn[1].encode('utf-8'),pr_rtn[2].encode('utf-8'))
#print(rtn.replace('\\','\\\\'))
#print(sys.getdefaultencoding())

if __name__ == '__main__':
    pr_mean,pr_rtn = predic([255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,0,118,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,162,0,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,44,0,255,255,255,0,0,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,51,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,0,32,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,0,8,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,0,17,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,109,0,101,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,239,255,255,255,255,255,255,255,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,255,255,255,255,255,255,135,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,0,0,15,15,15,9,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,0,0,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,0,0,0,99,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,0,255,255,255,255,255,7,0,0,0,110,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,84,255,255,255,255,255,255,255,255,0,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,53,255,255,255,255,255,255,255,255,255,255,0,0,0,138,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,52,255,255,255,255,255,255,255,255,255,255,255,250,0,0,0,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,0,106,255,255,255,255,255,255,255,255,255,255,255,255,255,251,203,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255])
    print(pr_rtn,pr_mean)
    #train()