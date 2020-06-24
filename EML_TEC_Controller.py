from easyhid import Enumeration
from binreader import BinaryReader
from io import BytesIO
import time
import struct
from enum import Enum, auto, unique

# the size of the HID output report.
HID_REPORT_OUT_SIZE = 8

# the size of the HID intput report.
HID_REPORT_IN_SIZE = 100

@unique
class SysCommand(Enum):
    SET_TEMP_CONT_LEV = 1
    SET_VLIM = auto()
    SET_ILIM = auto()
    SET_TARGET_TEMP = auto()
    SET_AUTOTUNING = auto()
    SET_TEC_MODE = auto()
    SET_PID_P = 0x10
    SET_PID_I = auto()
    SET_PID_D = auto()
    SET_SAMP_INTR = auto()
    SAV_PARAM = 0x20
    RES_PARA = auto()
    SET_PS_VALUES = 0x30
    SET_IBIAS_VALUES = auto()

@unique
class Channel(Enum):
    CH1 = 0
    CH2 = auto()
    CH3 = auto()
    CH4 = auto()

@unique
class VSourceCommand(Enum):
    VD = 1
    VG = auto()
    VC = auto()
    VEA = auto()
    SHUTDOWN = 10
    POWERON = auto()

@unique
class ISourceCommand(Enum):
    Current = 1
    SHUTDOWN = 10
    POWERON = auto()

class Controller():

    def __init__(self):

        en = Enumeration()
        devices = en.find(vid=1155, pid=22352, serial="EMLTEC0003A1")

        for dev in devices:
            print(dev.serial_number)

        if len(devices) == 0:
            raise Exception("unable to find the board.")
            
        self.dev = devices[0]
        self.dev.open()

    def __del__(self):
        if self.dev != None:
            self.dev.close()

    def __send_command(self, command, para):
        
        stream = BytesIO()

        # stream.write(b'\x01') # Report ID should be 1
        stream.write(struct.pack('c', bytes([command.value])))

        if type(para) == int:
            stream.write(struct.pack('i', para))
        elif type(para) == float:
            stream.write(struct.pack('f', para))
        elif type(para) == bytes:
            stream.write(para)
        else:
            raise ValueError('illegal type of the parameter.')

        cnt = stream.getbuffer().nbytes
        if cnt < HID_REPORT_OUT_SIZE:
            stream.write(bytes(range(HID_REPORT_OUT_SIZE - cnt)))
        elif cnt > HID_REPORT_OUT_SIZE:
            raise ValueError('the HID output report is too long.')

        # read the byte array and send to the HID device.
        stream.seek(0)
        data = stream.read()
        stream.close()

        print([ "0x%02x" % b for b in data ])

        self.dev.write(data, 1) # report id is 0x1

    def __send_command_subchannel(self, command, channel, subcommand, para):

        stream = BytesIO()
        stream.write(bytes([channel.value, subcommand.value]))

        if type(para) == int:
            stream.write(struct.pack('h', para)) # unsigned short
        elif type(para) == float:
            stream.write(struct.pack('f', para))
        else:
            raise ValueError('illegal type of the parameter.')
        
        stream.seek(0)
        data = stream.read()
        stream.close()

        print([ "0x%02x" % b for b in data ])
        self.__send_command(command, data)

    def SetTargetTemperature(self, targetTemp):
        if type(targetTemp) != float:
            raise ValueError('the temperature must be float.')
        elif targetTemp < -60 or targetTemp > 120:
            raise ValueError('the temperature must be -60 to 120.')
        else:
            self.__send_command(SysCommand.SET_TARGET_TEMP, int(targetTemp * 100))

    def SetPID_P(self, value):
        if type(value) != float:
            raise ValueError('the P must be float.')
        else:
            self.__send_command(SysCommand.SET_PID_P, value)

    def SetPID_I(self, value):
        if type(value) != float:
            raise ValueError('the I must be float.')
        else:
            self.__send_command(SysCommand.SET_PID_I, value)

    def SetPID_D(self, value):
        if type(value) != float:
            raise ValueError('the D must be float.')
        else:
            self.__send_command(SysCommand.SET_PID_D, value)

    def SETPID_SamplingInterval(self, millisec):
        if type(millisec) != int:
            raise ValueError('the PID sampling interval must be int.')
        elif  millisec <= 0:
            raise ValueError('the PID sampling interval must be larger than 0.')
        else:
            self.__send_command(SysCommand.SET_SAMP_INTR, millisec)

    def StartPID_AutoTuning(self):
        self.__send_command(SysCommand.SET_AUTOTUNING, 1)

    def StopPID_AutoTuning(self):
        self.__send_command(SysCommand.SET_AUTOTUNING, 0)

    def SavePID_Param(self):
        self.__send_command(SysCommand.SAV_PARAM, 1)

    def RestorePID_Param(self):
        self.__send_command(SysCommand.RES_PARA, 1)

    def SetVD(self, channel, volt):
        if type(volt) != float:
            raise ValueError('the VD must be float.')
        elif volt < 0 or volt > 2.5:
            raise ValueError('the VD must be 0V to 2.5V.')
        else:
            self.__send_command_subchannel(SysCommand.SET_PS_VALUES, channel, VSourceCommand.VD, int(volt * 1000))

    def SetVEA(self, channel, volt):
        if type(volt) != float:
            raise ValueError('the VEA must be float.')
        elif volt < -3 or volt > 0:
            raise ValueError('the VEA must be -3V to 0V.')
        else:
            self.__send_command_subchannel(SysCommand.SET_PS_VALUES, channel, VSourceCommand.VEA, int(volt * 1000))

    def VSourceON(self, channel):
        self.__send_command_subchannel(SysCommand.SET_PS_VALUES, channel, VSourceCommand.POWERON, int(0))

    def VSourceOFF(self, channel):
        self.__send_command_subchannel(SysCommand.SET_PS_VALUES, channel, VSourceCommand.SHUTDOWN, int(0))

        # !! NOTE: the power off costs about 1s because of the requirement of the VD, VC, VG, VEA power off sequence.
        time.sleep(1)
            
    def SetIBias(self, channel, mA):
        if type(mA) != float:
            raise ValueError('the IBias must be float.')
        elif mA < 0 or mA > 150:
            raise ValueError('the IBias must be 0mA to 150mA.')
        else:
            self.__send_command_subchannel(SysCommand.SET_IBIAS_VALUES, channel, ISourceCommand.Current, int(mA * 100))

    def ISourceON(self, channel):
        self.__send_command_subchannel(SysCommand.SET_IBIAS_VALUES, channel, ISourceCommand.POWERON, int(0))

    def ISourceOFF(self, channel):
        self.__send_command_subchannel(SysCommand.SET_IBIAS_VALUES, channel, ISourceCommand.SHUTDOWN, int(0))

    def ReadMonitoringData(self):
        data = self.dev.read(size=HID_REPORT_IN_SIZE, timeout=1000)

        print(f'{len(data)} bytes read.')

        # !! IMPORTANT !!
        # You should convert the byte array to the BinaryIO
        # Refer to https://github.com/jleclanche/binreader/blob/master/binreader.py
        f = BytesIO(data)
        reader = BinaryReader(f)

        # ignore the Report ID
        reader.read_byte()
        
        # TEC parameters parser.
        self.RealTimeTemp = reader.read_int16() / 100.0
        self.VTEC = reader.read_int16() / 1000
        self.ITEC = reader.read_int16() / 1000
        tempManualCtrl = reader.read_int16() # Obsoleted
        self.VLIM = reader.read_int16()
        self.ILIM = reader.read_int16()
        self.TargetTemp = reader.read_int16() / 100
        self.PIDSamplingInterval = reader.read_int16()
        self.PID_P = reader.read_float()
        self.PID_I = reader.read_float()
        self.PID_D = reader.read_float()

        # Power Supplier parameters parser.
        self.VD = []
        self.VC = []
        self.VG = []
        self.VEA = []
        self.IEA = []

        for ch in range(0, 4):
            self.VD.append(reader.read_int16() / 1000)
            self.VC.append(reader.read_int16() / 1000)
            self.VG.append(reader.read_int16() / 1000)
            self.VEA.append(reader.read_int16() / 1000)
            self.IEA.append(reader.read_float())

        # IBias Source parameters parser.
        self.VF = []
        self.IBais = []

        for ch in range(0, 4):
            self.VF.append(reader.read_int16() / 1000)
            self.IBais.append(reader.read_int16() / 100)

        f.close()


if __name__ == "__main__":
    board = Controller()

    '''
    print(list(SysCommand))
    print(list(Channel))
    print(list(VSourceCommand))
    '''

    while True:
        board.ReadMonitoringData()
        print(f'Target Temp: {board.TargetTemp}℃')
        print(f"RT-Temp: {board.RealTimeTemp}℃")
        print(f'VD1: {board.VD[0]}V')
        time.sleep(0.001)

        board.SetVD(Channel.CH1, 1.761)
        board.SetVEA(Channel.CH1, -1.35)
        board.SetTargetTemperature(45.6)
        time.sleep(0.001)

        board.VSourceON(Channel.CH1)
        time.sleep(0.5)
        board.VSourceOFF(Channel.CH1)

        board.ReadMonitoringData()
        print(f'Target Temp: {board.TargetTemp}℃')
        print(f"RT-Temp: {board.RealTimeTemp}℃")
        print(f'VD1: {board.VD[0]}V')