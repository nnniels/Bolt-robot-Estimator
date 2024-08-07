

import numpy as np

from bolt_estimator.utils.Utils import utils, Log
from bolt_estimator.utils.TrajectoryGenerator import TrajectoryGenerator, Metal
from bolt_estimator.utils.Graphics import Graphics
from bolt_estimator.estimator.Filter_Complementary import ComplementaryFilter

from bolt_estimator.data.DataReader import DataReader


'''
A code to test a filter.

Outputs all data as graphs

'''



class Test_Filter():
    def __init__(self, filter_type="complementary",
                        parameters=(1/1000, 2),
                        optparameters = (100, 0.005),
                        name="Standard complementary"):
            self.filter_type=filter_type
            self.parameters=parameters
            self.optparameters = optparameters
            self.name = name

    def TestDim(self, desired_dim, inputed_dim):
        testlogger = Log("testing dimension input ", print_on_flight=True)
        print("# ", self.optparameters)
        memsize, integratorgain = self.optparameters
        filter = ComplementaryFilter(self.parameters, ndim=desired_dim, talkative=True, name=self.name, logger=testlogger, memory_size=memsize, offset_gain=integratorgain)
        x = np.ones(inputed_dim)
        xdot = np.ones(inputed_dim)
        filter.RunFilter(x, xdot)



    def RunTest(self, N, noise_level, datatype):
        # generate useful objects
        testlogger = Log("test " + datatype + " with noise level " + str(noise_level), print_on_flight=True)
        grapher = Graphics(logger=testlogger)

        # load custom data
        if datatype=="custom":
            pcom = np.load("./miscanellous/com_pos_superplus.npy")
            vcom = np.load("./miscanellous/vcom_pos_superplus.npy")
            
            trajX = pcom[0, :, 0]
            trajY = pcom[0, :, 1]
            trajZ = pcom[0, :, 2]
            adapted_traj = np.array([trajX, trajY, trajZ])
            speedX = vcom[0, :, 0]
            speedY = vcom[0, :, 1]
            speedZ = vcom[0, :, 2]
            adapted_speed = np.array([speedX, speedY, speedZ])
            print(" # shape ", adapted_speed.shape)

            # number of samples
            N=max(pcom.shape)
            ndim=3

            # start generator
            generator = TrajectoryGenerator(logger=testlogger)
            generator.Generate(datatype, noise_level=noise_level, N=N, traj=adapted_traj)


        elif datatype=="simulated":
            datatype="custom"
            reader = DataReader(testlogger)
            reader.AutoLoad(4)
            a = reader.Get("a")[:, 1, :].copy()
            v = reader.Get("v")[:, 1, :].copy()
            
            adapted_traj = np.array([v[:, 0], v[:, 1], v[:, 2]])
            adapted_speed = np.array([a[:, 0], a[:, 1], a[:, 2]])
            print(" # shape ", adapted_speed.shape)

            # number of samples
            N=max(v.shape)
            ndim=3

            # start generator
            generator = TrajectoryGenerator(logger=testlogger)
            generator.Generate(datatype, noise_level=noise_level, N=N, traj=adapted_traj)
        
        elif datatype=="simulated 1D":
            datatype="custom"
            reader = DataReader(testlogger)
            reader.AutoLoad(4)
            a = reader.Get("a")[:, 1, 2].copy()
            v = reader.Get("v")[:, 1, 2].copy()
            
            adapted_traj = np.array([v])
            adapted_speed = np.array([a])
            print(" # shape ", adapted_speed.shape)

            # number of samples
            N=max(v.shape)
            ndim=1

            # start generator
            generator = TrajectoryGenerator(logger=testlogger)
            generator.Generate(datatype, noise_level=noise_level, N=N, traj=adapted_traj)


        else : 
            # start generator
            generator = TrajectoryGenerator(logger=testlogger)
            generator.Generate(datatype, noise_level=noise_level, N=N, amplitude=0.1)
            ndim=1
        
        if self.filter_type == "complementary":
            print(" # optparams ", self.optparameters)
            print(" # ndim ", ndim)
            memsize, integratorgain = self.optparameters
            self.filter = ComplementaryFilter(self.parameters, ndim=ndim, talkative=True, name=self.name, logger=testlogger, memory_size=memsize, offset_gain=integratorgain)
            
        # empty filter data filter
        filter_traj = np.zeros((ndim, N))

        # get data
        true_traj, true_speed, true_acc = generator.GetTrueTraj()
        noisy_traj, noisy_speed, noisy_acc = generator.GetNoisyTraj()

        # run filter over time, with noisy data as inputs
        for k in range(N):
            filter_traj[:, k] = self.filter.RunFilter(np.array(noisy_traj[:,k]), np.array(noisy_speed[:,k]) )

        # plotting
        dataset = [noisy_traj, true_traj, filter_traj]
        grapher.SetLegend(["Noisy position (" + str(noise_level) + "%)", "True pos", "Filter out pos"], ndim)
        grapher.CompareNDdatas(dataset, "position", "Output on " + datatype + " traj. with noise level " + str(noise_level) + "\n to filter " + self.filter.name, style_adapter=False)

        # plotting error
        scaler = abs(np.max(true_traj) / np.min(true_traj))
        scaled_error = abs(true_traj-filter_traj)/scaler
        dataset = [scaled_error]
        print(" error coeff : ", np.sum(scaled_error))
        grapher.SetLegend(["error of the filter " + self.filter.name], ndim)
        grapher.CompareNDdatas(dataset, "position", "Error on " + datatype + " traj. with noise level " + str(noise_level) + "\n to filter " + self.filter.name, style_adapter=False, width=0.5)
        grapher.end()




# the number of samples on which to test the filter
N = 1000
# the desired level of noise in the signal to be filtered
noise_level=40
# the filter to test
filter_type =  "complementary"
parameters=(1/N, 0.04)
optparameters = (50, 0.02)
name="Standard complementary"




TF = Test_Filter(filter_type, parameters, optparameters, name=name)
# TF.TestDim(3, 3)
# TF.RunTest(N, noise_level=10, datatype="polynomial")
# TF.RunTest(N, noise_level=40, datatype="sinus")
# TF.RunTest(N, noise_level=30, datatype="polynomial9")
# TF.RunTest(N, noise_level=20, datatype="custom")
# TF.RunTest(N, noise_level=20, datatype="simulated")
TF.RunTest(N, noise_level=5, datatype="simulated 1D")












