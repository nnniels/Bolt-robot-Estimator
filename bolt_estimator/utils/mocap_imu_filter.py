#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 21 12:16:08 2024

@author: niels
"""

from bolt_estimator.estimator.Filter_Complementary import ComplementaryFilter
import numpy as np
import matplotlib.pyplot as plt

class MocapIMUFilter():
    def __init__(self,
                 parameters_sf = [2],
                 parameters_af = [1.1],
                 parameters_pf = [2],
                 filter_speed=True,
                 filter_attitude=False,
                 filter_position=False,
                 dt = 0.001,
                 logging=0,
                 talkative=False
                 ):
        # params
        self.time_step = dt
        self.iter = 0
        self.logging = logging
        self.FS = filter_speed
        self.FA = filter_attitude
        self.FP = filter_position

        self.learning_iter = 0
        self.omega_bias = np.zeros((3,))
        self.a_bias = np.zeros((3,))

        
        # filters params
        parameters_sf = [self.time_step] + parameters_sf
        parameters_af = [self.time_step] + parameters_af
        parameters_pf = [self.time_step] + parameters_pf

        self.SpeedFilter = ComplementaryFilter(parameters=parameters_sf, 
                                                name="speed complementary filter", 
                                                talkative=talkative, 
                                                logger=None, 
                                                ndim=3,
                                                memory_size=100,
                                                offset_gain=0.005)
        self.PositionFilter = ComplementaryFilter(parameters=parameters_pf, 
                                                name="speed complementary filter", 
                                                talkative=talkative, 
                                                logger=None, 
                                                ndim=3)
        self.AttitudeFilter = ComplementaryFilter(parameters=parameters_af, 
                                                name="attitude complementary filter", 
                                                talkative=talkative, 
                                                logger=None, 
                                                ndim=3)
        if talkative: print("Mocap IMU filter initialized")
        
        if self.logging != 0 :
            self.InitLogs()
        
        return None
    
    def InitLogs(self):
        self.p_logs = np.zeros((self.logging, 3))
        self.v_logs = np.zeros((self.logging, 3))
        self.q_logs = np.zeros((self.logging, 4))
        self.w_logs = np.zeros((self.logging, 3))

        self.p_logs_mocap = np.zeros((self.logging, 3))
        self.v_logs_mocap = np.zeros((self.logging, 3))
        self.q_logs_mocap = np.zeros((self.logging, 4))

        self.a_logs_imu = np.zeros((self.logging, 3))

        
    def UpdateLogs(self, p, v, q, w, p_mocap, v_mocap, q_mocap, a_imu):
        if self.iter>=self.logging :
            return None
        self.p_logs[self.iter, :] = p[:]
        self.v_logs[self.iter, :] = v[:]
        self.q_logs[self.iter, :] = q[:]
        self.w_logs[self.iter, :] = w[:]

        self.p_logs_mocap[self.iter, :] = p_mocap[:]
        self.v_logs_mocap[self.iter, :] = v_mocap[:]
        self.q_logs_mocap[self.iter, :] = q_mocap[:]

        self.a_logs_imu[self.iter, :] = a_imu[:]
        return None
    
    def GetLogs(self, data="position"):
        if self.logging==0:
            print("no logs stored")
            return None
        if data=="position":
            return self.p_logs
        elif data=="speed":
            return self.v_logs
        elif data=="theta" or data=="quat":
            return self.q_logs
        elif data=="omega":
            return self.w_logs
        else :
            print("wrong data getter")

    def LearnIMUBias(self, a_imu, omega_imu):
        self.a_bias = (self.learning_iter * self.a_bias + a_imu)/(self.learning_iter + 1)
        self.omega_bias = (self.learning_iter * self.omega_bias + omega_imu)/(self.learning_iter + 1)
        print("learning")
    
    def PlotLogs(self):
        if self.logging==0:
            print("no logs stored")
            return None
        plt.clf()
        
        plt.figure()
        plt.grid()
        plt.title("position out")
        plt.plot(self.p_logs[:, 0], label="position X out")
        plt.plot(self.p_logs[:, 1], label="position Y out")
        plt.plot(self.p_logs[:, 2], label="position Z out")
        plt.legend()
        
        plt.figure()
        plt.grid()
        plt.title("speed out")
        plt.plot(self.v_logs[:, 0], label="speed X out")
        plt.plot(self.v_logs[:, 1], label="speed Y out")
        plt.plot(self.v_logs[:, 2], label="speed Z out")
        plt.legend()

        # plt.figure()
        # plt.grid()
        # plt.title("speed derived from position out")
        # plt.plot(self.p_logs[1:, 0] - self.p_logs[:-1, 0]*1.6, label="computed speed X for 1600Hz") # HARD CODED
        # plt.legend()


        plt.figure()
        plt.grid()
        plt.title("speed X comparison")
        plt.plot(self.v_logs_mocap[:, 0], label="speed X mocap")
        plt.plot(self.v_logs[:, 0], label="speed X out")
        plt.legend()
        
        plt.figure()
        plt.grid()
        plt.title("attitude")
        plt.plot(self.q_logs, label="quaternion attitude")
        plt.legend()
        
        plt.figure()
        plt.grid()
        plt.title("angular speed")
        plt.plot(self.w_logs[:, 0], label="angular speed X out")
        plt.plot(self.w_logs[:, 1], label="angular speed Y out")
        plt.plot(self.w_logs[:, 2], label="angular speed Z out")
        plt.legend()

        plt.figure()
        plt.grid()
        plt.title("acceleration imu")
        plt.plot(self.a_logs_imu[:, 0], label="acc X imu")
        plt.plot(self.a_logs_imu[:, 1], label="acc Y imu")
        plt.plot(self.a_logs_imu[:, 2], label="acc Z imu")
        plt.legend()
        
        plt.show()

    def de_biasIMU(self, acc, accg, gyro):
        return acc-self.a_bias, accg-self.a_bias, gyro-self.omega_bias
    
    
    def Run(self, p_mocap, v_mocap, quat_mocap, omega_imu, a_imu, dt=None, de_bias=False):
        if de_bias : 
            # correct learned bias
            a_imu_corr = a_imu - self.a_bias
            omega_imu_corr = omega_imu - self.omega_bias
        else :
            # bias is already corrected
            a_imu_corr = a_imu
            omega_imu_corr = omega_imu


        # initialize data
        p_out = np.copy(p_mocap)
        v_out = np.copy(v_mocap)
        quat_out = np.copy(quat_mocap)
        omega_out = np.copy(omega_imu_corr)
        
        
        
        # filter speed
        v_filter = self.SpeedFilter.RunFilter(v_mocap, a_imu_corr, dt)
        # filter attitude
        quat_filter = self.AttitudeFilter.RunFilterQuaternion(quat_mocap, omega_imu_corr, dt)
        # filter position
        p_filter = self.PositionFilter.RunFilter(p_mocap, v_filter, dt)
        
        if self.FP:
            p_out = p_filter
        if self.FS:
            v_out = v_filter
        if self.FA :
            quat_out = quat_filter
        
        if self.logging != 0 :
            self.UpdateLogs(p_out, v_out, quat_out, omega_out, p_mocap, v_mocap, quat_mocap, a_imu)
        
        self.iter += 1
        
        return p_out, v_out, quat_out, omega_out
    
    
    
    
    