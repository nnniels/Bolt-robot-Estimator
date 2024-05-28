import numpy as np
import pinocchio as pin


"""
Created on Wed May 22 13:41:35 2024

@author: nalbrecht

This is an implementation of Lyapunov-stable orientation estimator for humanoid robots, 2020

It is meant to work as a tilt and speed estimator for Bolt bipedal robot.
Encoders data, IMU data and pinocchio are used.
"""


class TiltEstimator():
    
    def __init__(self,
                 robot,
                 Q0,
                 Qd0,
                 Niter, 
                 params)-> None:
        """ initialize variables """
        # iter 
        self.iter = 0
        self.Niter = Niter
        # pinocchio
        self.Q = Q0
        self.Qd = Qd0
        self.bolt = robot
        self.data = self.bolt.model.createData()
        pin.forwardKinematics(self.bolt.model, self.data, self.Q)
        pin.updateFramePlacements(self.bolt.model, self.data)
        
        # state variables
        m  = 1/np.sqrt(3)
        self.x1_hat = np.zeros(3)
        self.x1_hat_dot = np.zeros(3)
        self.x2_hat = np.array([0, 0, 1.])
        self.x2_hat_dot = np.array([0, 0, 0])
        self.x2_prime = np.array([0, 0, 1.])
        self.x2_prime_dot = np.array([0, 0, 0])
        
        # errors
        self.x1_tilde = np.zeros(3)
        self.x2_tilde = np.zeros(3)
        self.x2_tildeprime = np.zeros(3)
        
        # utilities
        self.c_R_l = np.eye(3)
        self.prev_c_R_l = np.eye(3)
        
        # constants
        self.g0 = -9.81
        
        # logs
        self.InitLogs()

        # parameters
        self.alpha1, self.alpha2, self.gamma = params

        return None
    
    
    def InitLogs(self)-> None :
        """ create log matrixes"""
        # state variables
        self.x1_hat_logs = np.zeros((self.Niter,3))
        self.x2_hat_logs = np.zeros((self.Niter, 3))
        self.x2_prime_logs = np.zeros((self.Niter, 3))
        
        # errors
        self.x1_tilde_logs = np.zeros((self.Niter,3))
        self.x2_tilde_logs = np.zeros((self.Niter, 3))
        self.x2_tildeprime_logs = np.zeros((self.Niter, 3))
        
        return None
    
    
    def UpdateLogs(self) -> None:
        """ update log matrixes"""
        # state variables
        self.x1_hat_logs[self.iter, :] = self.x1_hat[:]
        self.x2_hat_logs[self.iter, :] = self.x2_hat[:]
        self.x2_prime_logs[self.iter, :] = self.x2_prime[:]
        
        # errors
        self.x1_tilde_logs[self.iter, :] = self.x1_tilde[:]
        self.x2_tilde_logs[self.iter, :] = self.x2_tilde[:]
        self.x2_tildeprime_logs[self.iter, :] = self.x2_tildeprime[:]
        return None
    
    
    def S(self, x:np.ndarray) -> np.ndarray:
        """ Skew-symetric operator """
        sx = np.array([[0,    -x[2],  x[1]],
                       [x[2],   0,   -x[0]],
                       [-x[1], x[0],    0 ]])
        return sx
    
    
    def GetYV_v1(self) -> np.ndarray:
        """ Estimate Yv and return it """
        yv = self.c_R_l.T @ self.c_Pdot_l + self.S(self.yg - self.c_Omega_l) @ self.c_R_l.T @ self.c_P_l
        return yv

    
    def GetYV_v2(self, LFootID, RFootID, BaseID, eta) -> np.ndarray:
        """ Estimate Yv and return it. This computation is an updated version, which is not present in the original paper """
        c_P_anchor = eta *  self.data.oMf[LFootID].translation + (1-eta) * self.data.oMf[RFootID].translation
        v1 = pin.getFrameVelocity(self.bolt.model, self.data, LFootID)
        v2 = pin.getFrameVelocity(self.bolt.model, self.data, RFootID)
        c_Pdot_anchor = eta *  v1.translation + (1-eta) * v2.translation
        yv = -self.S(self.yg) @ c_P_anchor - c_Pdot_anchor
        return yv

    
    def PinocchioUpdate(self, BaseID, ContactFootID, dt) -> None:
        """ Update pinocchio data with forward kinematics and update FK variables"""
        
        # update pinocchio data
        pin.forwardKinematics(self.bolt.model, self.data, self.Q)
        pin.computeAllTerms(self.bolt.model, self.data, self.Q, self.Qd)
        pin.updateFramePlacements(self.bolt.model, self.data)
        
        # update relevant data
        # rotation matrix of base frame (l) in contact foot frame (c)
        self.prev_c_R_l[:, :] = self.c_R_l.copy()
        self.c_R_l = np.array(self.data.oMf[BaseID].rotation.copy()) @ np.array(self.data.oMf[ContactFootID].rotation.copy()).T
        self.c_Rdot_l =  (self.c_R_l - self.prev_c_R_l) / dt # TODO : chk

        # position of base frame in contact foot frame
        self.c_P_l = np.array((self.data.oMf[ContactFootID].inverse()*self.data.oMf[BaseID]).translation).copy()
        #self.c_P_l = np.array(self.c_P_l.translation).copy()

        # speed of base frame in contact foot frame
        oMf = self.data.oMf[ContactFootID]
        c_speed_l = oMf.inverse().action @ pin.getFrameVelocity(self.bolt.model, self.data, BaseID, pin.WORLD)
        self.c_Pdot_l = np.array(c_speed_l[:3]).copy()

        # rotation speed of base frame in contact foot frame
        self.c_Omega_l = np.array(c_speed_l[3:]).copy()

        return None
    

    
    def ErrorUpdate(self, dt:float) -> None:
        """ Compute error in estimation and update error variables"""
        S2 = self.S(self.x2_hat)**2

        x1_tilde_dot      = -self.S(self.yg) @ self.x1_tilde - self.alpha1 * self.x1_tilde - self.g0*self.x2_tildeprime
        x2_tildeprime_dot = -self.S(self.yg) @ self.x2_tildeprime - self.alpha2/self.g0 * self.x1_tilde
        x2_tilde_dot      = -self.S(self.yg) @ self.x2_tilde - self.gamma * S2 @ (self.x2_tilde - self.x2_tildeprime)
        
        self.x1_tilde += x1_tilde_dot * dt
        self.x2_tilde += x2_tilde_dot * dt
        self.x2_tildeprime += x2_tildeprime_dot * dt
        
        return None

    
    
    def Estimate(self, 
                  Q:np.ndarray,
                  Qd:np.ndarray,
                  BaseID:int,
                  ContactFootID:int,
                  ya:np.ndarray, 
                  yg:np.ndarray, 
                  dt:float, 
                  ) -> tuple[np.ndarray, np.ndarray] : 
        """ update state variables and return current tilt and speed estimates """
        
        # store measurement
        self.ya = ya.copy()
        self.yg = yg.copy()
        # speed estimate
        self.Q = Q.copy()
        self.Qd = Qd.copy()
        self.PinocchioUpdate(BaseID, ContactFootID, dt)
        self.yv = self.GetYV_v1()
    
        
          
        # state variables derivatives update
        self.x1_hat_dot = - self.S(yg) @ self.x1_hat - self.g0*self.x2_prime + ya + self.alpha1*( self.yv - self.x1_hat)
        
        self.x2_prime_dot = -self.S(yg) @ self.x2_prime - self.alpha2/self.g0 * ( self.yv - self.x1_hat)
        
        self.x2_hat_dot = -self.S(yg - self.gamma*self.S(self.x2_hat) @ self.x2_prime) @ self.x2_hat
        
        
        # state variable integration
        self.x1_hat += dt * self.x1_hat_dot
        self.x2_hat += dt * self.x2_hat_dot
        self.x2_prime += dt * self.x2_prime_dot
        
        
        # error update
        self.ErrorUpdate(dt)
        
        # logging
        self.UpdateLogs()
        self.iter += 1

        #x3 = ya - self.S(yg)@self.x1_hat - self.x1_hat_dot
        
        # return estimated data
        return self.x1_hat, self.x2_hat
    
    














































