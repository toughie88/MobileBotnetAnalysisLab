# -*- coding: utf-8 -*-
# ############################################
##Sample data process V3.0
##Author:Xin Meng
##Data:  2014 Nov. 11th
##Description: Process the packet file and combinate the packet with same stream index into one stream
##             And generate the dataset based on the stream.
##             Use Stream maybe more accuracy
##             Now Let me fix the code
#############################################


import logging  # Log modurler
import os
import csv
import subprocess
import string
import sys

###################################################
###variable
###################################################
# configuration variable
from Tools.scripts.treesync import raw_input

OutputCSVDir = ""
ReportDir = ""
NormalDBDir = ""
InputNormalDir = ""
InputInfectDir = ""

output_csv_dir = ""
report_dir = ""
normal_db_dir = ""
input_normal_dir = ""
input_infect_dir = ""
normal_db_file = "normal_db.txt"
public_ip_range_file = "public_ip_range.txt"
output_extension = ".csv"
# remember if you want to change the global variance in function, you need use global xxx
normal_db_size = 0
#Current Path (the Script)
path = os.path.split(os.path.realpath(__file__))[0]
#The Scan Information
num_normal_input_file = 0
num_infect_input_file = 0
normal_input_file_list = []
infect_input_file_list = []
#Globle statistic information
num_normal_packet = 0
num_packet_label_infect = 0
num_packet_label_normal = 0
####################################################
########## FUNCTION: ip2int
########## INPUT:    IP
########## RETURN:   int of the IP
####################################################


def ip2int(ip):
    import struct
    import socket

    return struct.unpack("!I", socket.inet_aton(ip))[0]


####################################################
########## FUNCTION: int2ip
########## INPUT:    int of IP
########## RETURN:   IP
####################################################


def int2ip(i):
    import socket
    import struct

    return socket.inet_ntoa(struct.pack("!I", i))


####################################################
########## FUNCTION: change the IP/subset to IP range
########## Input: "216.239.32.0/19"
########## Return: IP range IP cmin cmax  216.239.32.0 216.239.63.255
####################################################
def subnet_mask_to_ip_range(iplist):
    data = iplist.split('/')
    ip = data[0]
    ti = int(data[1])
    d = int(ti / 8)
    c = 256 / (2 ** (ti % 8))
    ip_items = ip.split('.')
    if len(ip_items[d:]) == 1:
        if ti % 8 == 0:
            cmin = '%s.%s' % ('.'.join(ip_items[:d]), '0')
            cmax = '%s.%s' % ('.'.join(ip_items[:d]), '255')
        else:
            for i in range(2 ** (ti % 8)):
                mymax = (i + 1) * c - 1
                mymin = i * c
                data = int(''.join(ip_items[d:]))
                if data < mymax and data >= mymin:
                    cmin = '%s.%s' % ('.'.join(ip_items[:d]), mymin)
                    cmax = '%s.%s' % ('.'.join(ip_items[:d]), mymax)
    else:
        if ti % 8 == 0:
            cmin = '%s.%s.%s' % ('.'.join(ip_items[:d]), '0', ('0.' * (len(ip_items) - d - 1))[:-1])
            cmax = '%s.%s.%s' % ('.'.join(ip_items[:d]), '255', ('255.' * (len(ip_items) - d - 1))[:-1])
        else:
            for i in range(2 ** (ti % 8)):
                mymax = (i + 1) * c - 1
                mymin = i * c
                data = int(''.join(ip_items[d]))
                if data < mymax and data >= mymin:
                    cmin = '%s.%s.%s' % ('.'.join(ip_items[:d]), mymin, ('0.' * (len(ip_items) - d - 1))[:-1])
                    cmax = '%s.%s.%s' % ('.'.join(ip_items[:d]), mymax, ('255.' * (len(ip_items) - d - 1))[:-1])
    #print  cmin, cmax
    return (cmin, cmax)


####################################################
########## FUNCTION: decision for whether the IP in a IP range
########## Input: IP range string "216.239.32.0/19" (string) , IP (int) to decide
########## Return: 1 in the range
##########         0 not in the range
####################################################
def in_ip_range(subnet_mask_ip, ip):
    ip_range_lower, ip_range_upper = subnet_mask_to_ip_range(subnet_mask_ip)
    int_ip_lower = ip2int(ip_range_lower)
    int_ip_upper = ip2int(ip_range_upper)
    # print(int_ip_lower)
    # print(int_ip_upper)
    # print(ip)
    # print(ip_range_lower)
    # print(ip_range_upper)
    # print(int2ip(ip))
    if int_ip_upper >= ip >= int_ip_lower:
        return 1
    else:
        return 0


####################################################
########## FUNCTION: Load Configuration
########## RETURN: InputNormalDir
##########         InputInfectDir
##########         OutputCSVDir
##########         ReportDir
##########         NormalDBDir
####################################################


def load_conf():
    global output_csv_dir
    global report_dir
    global normal_db_dir
    global input_normal_dir
    global input_infect_dir
    #from __future__ import with_statement
    #DataProcess.cfg
    import ConfigParser

    config = ConfigParser.ConfigParser()
    with open(path + "\DataProcess_forPC_timestamp.cfg", "r") as cfgfile:
        #with open(path+"\DataProcess.cfg", "r") as cfgfile:
        config.readfp(cfgfile)
        input_dir = config.get("DIR", "InputDir")
        normal_dir = config.get("DIR", "NormalDir")
        infect_dir = config.get("DIR", "InfectDir")

        output_csv_dir = os.path.normcase(config.get("DIR", "OutputDir"))
        report_dir = os.path.normcase(config.get("DIR", "ReportDir"))
        normal_db_dir = os.path.normcase(config.get("DIR", "NormalDB"))

    input_normal_dir = os.path.normcase(input_dir + normal_dir)
    input_infect_dir = os.path.normcase(input_dir + infect_dir)

    #return (InputNormalDir,InputInfectDir,OutputCSVDir,ReportDir,NormalDBDir)


####################################################
########## FUNCTION: Scan the Input Data directory
####################################################


def scan_input_data():
    global num_normal_input_file
    global num_infect_input_file
    global normal_input_file_list
    global infect_input_file_list
    #Load Configuration File to get parameters
    load_conf()
    #List the normal and infect files
    logger.info(input_normal_dir)
    logger.info(input_infect_dir)

    normal_input_file_list = os.listdir(input_normal_dir)
    infect_input_file_list = os.listdir(input_infect_dir)
    num_normal_input_file = len(normal_input_file_list)
    num_infect_input_file = len(infect_input_file_list)

    logger.info(num_infect_input_file)
    logger.info(num_normal_input_file)
    #Show the result of scanning
    show_scan_result(1)


####################################################
########## FUNCTION: Show Help Information
####################################################


def show_help_info():
    print("================================================")
    print("=========MobileBotnetAnalysisLab (MBAL)=========")
    print("=========Version: V4.0                 =========")
    print("=========Develop: Xin Meng             =========")
    print("=========Date: 2014 Oct. 29th          =========")
    print("================================================")
    print("Help Information:")
    print("0: Scan the configuration and Show the information")
    print("1: Process the Normal Traffic File and construct the Normal Databas")
    print("2: Process the Infect Traffic File")
    print("3: Show the Help Information")
    print("4: extensions")
    print("9: Quit")
    print("================================================")


####################################################
########## FUNCTION1: Show Scanning Result
########## Input:     The level of show 0-Infect 1-Normal 2-Normal&Infect
####################################################


def show_scan_result(level=2):
    print("--------------------Scanning Result--------------------")
    if level > 0:
        print("The number of Normal file:" + str(num_normal_input_file))
        print("Files:")
        for i in range(0, num_normal_input_file):
            print("Input " + str(i + 1) + " to process: " + normal_input_file_list[i])
    if level < 1 or level > 1:
        print("The number of Infect file:" + str(num_infect_input_file))
        print("Files:")
        for i in range(0, num_infect_input_file):
            print("Input " + str(i + 1) + " to process: " + infect_input_file_list[i])
    print("--------------------Scanning End--------------------")

####################################################
##########Logger Configuration
####################################################
# 创建一个logger
logger = logging.getLogger('mainlogger')
logger.setLevel(logging.DEBUG)

# 创建一个handler，用于写入日志文件
fh = logging.FileHandler(path + '/mainlog.log')
fh.setLevel(logging.DEBUG)

# 再创建一个handler，用于输出到控制台
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# 定义handler的输出格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

# 给logger添加handler
logger.addHandler(fh)
logger.addHandler(ch)

# 记录一条日志
logger.info('Test mainlog')
# Set Level of the logger, 
# NOTSET < DEBUG < INFO < WARNING < ERROR < CRITICAL
#logger.setLevel(logging.WARNING)    #Show Debug Information
#logger.setLevel(logging.INFO)    #Show Debug Information
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.NOTSET)  #Not show Any Information

####################################################
########## FUNCTION: compare between normal packet with the normal database
########## Input: a: packet from traffic b: packet from normal database
####################################################


def compare(a, b):
    if a[0] == b[0] and a[1] == b[1] and a[2] == b[2]:
        return 1
    else:
        return 0


####################################################
########## FUNCTION: compare packet in infect traffic file with the packet in normal database,
##########           find whether the packet is normal or infect
########## Input: a: packet from infect traffic file b: packet from normal database
########## Return: 1 normal packet match with the packet in database
##########         0 infect packet not match the database
####################################################


def decision_normal_infect(a_normal_packet, b_infect_packet):
    #0 source IP
    #1 destination IP
    #we use the fuzzy matching to decide whether the packet in the database or not
    #example:  192.168.123.***
    #Step1: compare with google public IP address
    #Step2: wildcard of the last 3 number of the IP address

    #####Step 1
    #Load the public IP range address from database dir : public_ip_range.txt
    flag_public_range = 0
    with open(normal_db_dir + public_ip_range_file, 'a+') as public_ip_range:
        for public_ip_range_line in public_ip_range:
            #compare the b_infect_packet ip source or ip destination with the IP range whether in the range
            #Because there is one of the two IP is the mobile IP address, so we just find one of [0] [1]
            #in the range, we decide the packet is normal
            if 1 == in_ip_range(public_ip_range_line, b_infect_packet[0]) or \
                            1 == in_ip_range(public_ip_range_line, b_infect_packet[1]):
                flag_public_range = 1
                break
            else:
                flag_public_range = 0
    if 1 == flag_public_range:
        #the infect packet ip in the public ip range
        return 1
    else:
        ######Step 2
        #compare the ip and protocol with the normal database packet, we use fuzzy matching,
        infect_ip_source_str = int2ip(b_infect_packet[0])
        infect_ip_des_str = int2ip(b_infect_packet[1])
        normal_ip_source_str = int2ip(int(a_normal_packet[0]))
        normal_ip_des_str = int2ip(int(a_normal_packet[1]))
        infect_ip_source_str_array = infect_ip_source_str.split('.')
        infect_ip_des_str_array = infect_ip_des_str.split('.')
        normal_ip_source_str_array = normal_ip_source_str.split('.')
        normal_ip_des_str_array = normal_ip_des_str.split('.')

        # logger.debug(infect_ip_source_str)
        # logger.debug(infect_ip_des_str)
        # logger.debug(normal_ip_source_str)
        # logger.debug(normal_ip_des_str)
        #
        #
        # logger.debug(infect_ip_source_str_array)
        # logger.debug(infect_ip_des_str_array)
        # logger.debug(normal_ip_source_str_array)
        # logger.debug(normal_ip_des_str_array)
        # set the level of fuzzy
        # level = 3    xxx.xxx.xxx only match the first 3 ip number
        level = 3
        index = 0
        match_flag = 1
        while index < level:
            if infect_ip_source_str_array[index] == normal_ip_source_str_array[index] and \
                            infect_ip_des_str_array[index] == normal_ip_des_str_array[index]:
                index += 1
            else:
                match_flag = 0
                break
        if match_flag == 1:
            return 1
        else:
            return 0


####################################################
########## FUNCTION: Process Normal File
########## Input: The number of the files in the normal list
####################################################


def normal_process(normal_file_no):
    global normal_db_size
    #Stream: initial 2 dimensions array to store the packet base on the stream index

    tcp_stream = [[[0 for col in range(0)] for row in range(0)] for high in range(50000)]
    udp_stream = [[[0 for col in range(0)] for row in range(0)] for high in range(15000)]
    num_udp_stream = 0
    num_tcp_stream = 0

    process_normal_file = input_normal_dir + normal_input_file_list[normal_file_no - 1]
    print (process_normal_file)
    #Load Normal Packet database, if the file not exist, create it. And append the file every process
    #normal_db = open(normal_db_dir + normal_db_file, 'a+')
    normal_db_temp = [[0 for col in range(10)] for row in range(0)]
    with open(normal_db_dir + normal_db_file, 'a+') as normal_db:
        for normal_db_line in normal_db:
            #normal_db_array = normal_db_line.split()
            normal_db_line_array = normal_db_line.split()
            normal_db_temp += [normal_db_line_array]
            normal_db_size += 1
    #Open normal csv file and initial the head of the table
    #print (output_csv_dir + normal_input_file_list[normal_file_no - 1] + output_extension)
    with open(output_csv_dir + normal_input_file_list[normal_file_no - 1] + output_extension, 'wSb+') as csv_file:
        csv_writer = csv.writer(csv_file, dialect='excel')
        csv_writer.writerow(
            ['IP source', 'IP des', 'Protocol', 'Frame duration', 'UDP size', 'TCP size', 'Argument Count', 'TimeStamp',
             'Lable'])

    #Stream: The output file will store the stream information
    #process every line in the normal file
    # -e ip.src -e ip.dst -e ip.proto
    # -e frame.time_delta
    # -e udp.length -e udp.stream
    # -e tcp.len -e tcp.stream
    # -e http.request.uri
    #The structure of every line: 9 if
    # IP source 0 , IP destination 1, IP protocol 2,
    # Frame duration 3,
    # UDP size 4, UDP stream index 5,
    # TCP size 6, TCP stream index 7,
    # URL 8
    for txt_line in open(process_normal_file):
        txt_array = txt_line.split()
        #重新构造txt_array
        if 7 > len(txt_array):
            continue
        if len(txt_array[0]) <= 15:
            #IP地址长度大于255.255.255.255,则为IPv6
            IP_source = ip2int(txt_array[0])
            txt_array[0] = IP_source
            IP_des = ip2int(txt_array[1])
            txt_array[1] = IP_des

            if txt_array[2] != '17':
                #TCP 6 UDP 17
                #if not UDP, SET udp size AS 0
                txt_array.insert(4, '0')
                txt_array.insert(5, '0')
            if txt_array[2] != '6':
                txt_array.insert(6, '0')
                txt_array.insert(7, '0')
                txt_array.insert(8, '0')
            else:
                if len(txt_array) == 10:
                    #include the HTTP request uri
                    arg_num = txt_array.pop(8).count('=')
                    txt_array.insert(8, str(arg_num))
                else:
                    arg_num = 0
                    txt_array.insert(8, str(arg_num))
            # 9 --> timestamp
            # txt_array.insert(9, 'normal')
            txt_array.insert(10, 'normal')

            #Decisied whether the packet has already existed in the normal_db
            status = 0
            for i in normal_db_temp:
                if 1 == compare(i, txt_array):
                    status = 1
                    break
            if 0 == status:
                normal_db_temp += [txt_array]
                normal_db_size += 1
                #append the data into to database file
                with open(normal_db_dir + normal_db_file, 'a+') as normal_db:
                    #normal_db_array = normal_db_line.split()
                    n = 0
                    s = ""
                    while n < len(txt_array):
                        s += str(txt_array[n])
                        s += " "
                        n += 1
                    s += "\n"
                    #txt_array_convert = ' '.join(str(txt_array))
                    normal_db.writelines(s)

            #将该txt_array加入到 Stream中,最后将Stream写入CSV文件
            if '17' == txt_array[2]:
                # UDP process
                udp_stream[int(txt_array[5])].append(txt_array)

            elif '6' == txt_array[2]:
                # TCP process
                tcp_stream[int(txt_array[7])].append(txt_array)

    for packet_list in udp_stream:
        #组合udp_stream中的每个stream的packet,将信息存储在CSV文件中.
        if len(packet_list) != 0:
            # 8 ['IP source', 'IP des', 'Protocol', 'Frame duration', 'UDP size', 'TCP size', 'Argument Count', 'Lable'])
            stream_temp = [0 for col in range(9)]
            stream_temp[0] = packet_list[0][0]
            stream_temp[1] = packet_list[0][1]
            stream_temp[2] = packet_list[0][2]
            for packet in packet_list:
                stream_temp[3] += float(packet[3])
                stream_temp[4] += int(packet[4])
            stream_temp[5] = 0
            stream_temp[6] = 0
            stream_temp[7] = packet_list[0][9]
            stream_temp[8] = packet_list[0][10]
            #Write the CSV file for the normal files.
            with open(output_csv_dir + normal_input_file_list[normal_file_no - 1] + output_extension, 'ab+') \
                    as csv_file:
                csv_writer = csv.writer(csv_file, dialect='excel')
                csv_writer.writerow(stream_temp)
            num_udp_stream += 1
    for packet_list in tcp_stream:
        #组合udp_stream中的每个stream的packet,将信息存储在CSV文件中.
        if len(packet_list) != 0:
            # 8 ['IP source', 'IP des', 'Protocol', 'Frame duration', 'UDP size', 'TCP size', 'Argument Count', 'Lable'])
            stream_temp = [0 for col in range(9)]
            stream_temp[0] = packet_list[0][0]
            stream_temp[1] = packet_list[0][1]
            stream_temp[2] = packet_list[0][2]
            for packet in packet_list:
                stream_temp[3] += float(packet[3])
                stream_temp[5] += int(packet[6])
                stream_temp[6] += int(packet[8])
            stream_temp[4] = 0
            stream_temp[7] = packet_list[0][9]
            stream_temp[8] = packet_list[0][10]
            #Write the CSV file for the normal files.
            with open(output_csv_dir + normal_input_file_list[normal_file_no - 1] + output_extension, 'ab+') \
                    as csv_file:
                csv_writer = csv.writer(csv_file, dialect='excel')
                csv_writer.writerow(stream_temp)
            num_tcp_stream += 1


####################################################
########## FUNCTION: Process Normal File
########## Input: The number of the files in the normal list
####################################################


def infect_process(infect_file_no):
    global num_packet_label_infect
    global num_packet_label_normal
    logger.info("Start to process the infect file")
    tcp_stream = [[[0 for col in range(0)] for row in range(0)] for high in range(50000)]
    udp_stream = [[[0 for col in range(0)] for row in range(0)] for high in range(15000)]
    num_udp_stream = 0
    num_tcp_stream = 0

    process_infect_file = input_infect_dir + infect_input_file_list[infect_file_no - 1]
    print (process_infect_file)
    #Load Normal Packet database, if the file not exist, create it. And append the file every process
    #normal_db = open(normal_db_dir + normal_db_file, 'a+')
    normal_db_temp = [[0 for col in range(10)] for row in range(0)]
    with open(normal_db_dir + normal_db_file, 'a+') as normal_db:
        for normal_db_line in normal_db:
            #normal_db_array = normal_db_line.split()
            normal_db_line_array = normal_db_line.split()
            normal_db_temp += [normal_db_line_array]
    #Open normal csv file and initial the head of the table
    #print (output_csv_dir + normal_input_file_list[normal_file_no - 1] + output_extension)
    with open(output_csv_dir + infect_input_file_list[infect_file_no - 1] + output_extension, 'wSb+') as csv_file:
        csv_writer = csv.writer(csv_file, dialect='excel')
        csv_writer.writerow(
            ['IP source', 'IP des', 'Protocol', 'Frame duration', 'UDP size', 'TCP size', 'Argument Count', 'TimeStamp',
             'Lable'])
    #process every line in the normal
    num_txt_line = 0
    for txt_line in open(process_infect_file):
        logger.info("Process the txt line: " + str(num_txt_line))
        num_txt_line += 1
        txt_array = txt_line.split()
        if 7 > len(txt_array):
            continue
        if len(txt_array[0]) <= 15:
            #IP地址长度大于255.255.255.255,则为IPv6
            IP_source = ip2int(txt_array[0])
            txt_array[0] = IP_source
            IP_des = ip2int(txt_array[1])
            txt_array[1] = IP_des

            if txt_array[2] != '17':
                #TCP 6 UDP 17
                #if not UDP, SET udp size AS 0
                txt_array.insert(4, '0')
                txt_array.insert(5, '0')
            if txt_array[2] != '6':
                txt_array.insert(6, '0')
                txt_array.insert(7, '0')
                txt_array.insert(8, '0')
            else:
                if len(txt_array) == 8:
                    #include the HTTP request uri
                    arg_num = txt_array.pop(8).count('=')
                    txt_array.insert(8, str(arg_num))
                else:
                    arg_num = 0
                    txt_array.insert(8, str(arg_num))

            #Decisied whether the packet is Normal or Infect
            #We use some algorithms to compare with the normal database, and
            #status = 1 : normal packet match the database
            #status = 0 : infect packet not match the database
            status = 0
            for i in normal_db_temp:
                if 1 == decision_normal_infect(i, txt_array):
                    status = 1
                    txt_array.insert(10, 'normal')
                    num_packet_label_normal += 1
                    break
            if 0 == status:
                txt_array.insert(10, 'infect')
                num_packet_label_infect += 1

            #将该txt_array加入到 Stream中,最后将Stream写入CSV文件
            if '17' == txt_array[2]:
                # UDP process
                udp_stream[int(txt_array[5])].append(txt_array)
                # print(int(txt_array[5]))
            elif '6' == txt_array[2]:
                # TCP process
                tcp_stream[int(txt_array[7])].append(txt_array)
                # print(int(txt_array[7]))
    logger.info("Start to write the csv file")
    for packet_list in udp_stream:
        #组合udp_stream中的每个stream的packet,将信息存储在CSV文件中.
        if len(packet_list) != 0:
            # 8 ['IP source', 'IP des', 'Protocol', 'Frame duration', 'UDP size', 'TCP size', 'Argument Count', 'Lable'])
            stream_temp = [0 for col in range(9)]
            stream_temp[0] = packet_list[0][0]
            stream_temp[1] = packet_list[0][1]
            stream_temp[2] = packet_list[0][2]
            for packet in packet_list:
                stream_temp[3] += float(packet[3])
                stream_temp[4] += int(packet[4])
            stream_temp[5] = 0
            stream_temp[6] = 0
            stream_temp[7] = packet_list[0][9]
            stream_temp[8] = packet_list[0][10]
            #Write the CSV file for the normal files.
            with open(output_csv_dir + infect_input_file_list[infect_file_no - 1] + output_extension, 'ab+') \
                    as csv_file:
                csv_writer = csv.writer(csv_file, dialect='excel')
                csv_writer.writerow(stream_temp)

            num_udp_stream += 1
    logger.info("Finish UDP CSV write, the sum of stream: " + str(num_udp_stream))
    for packet_list in tcp_stream:
        #组合udp_stream中的每个stream的packet,将信息存储在CSV文件中.
        if len(packet_list) != 0:
            # 8 ['IP source', 'IP des', 'Protocol', 'Frame duration', 'UDP size', 'TCP size', 'Argument Count', 'Lable'])
            stream_temp = [0 for col in range(9)]
            stream_temp[0] = packet_list[0][0]
            stream_temp[1] = packet_list[0][1]
            stream_temp[2] = packet_list[0][2]
            for packet in packet_list:
                stream_temp[3] += float(packet[3])
                stream_temp[5] += int(packet[6])
                stream_temp[6] += int(packet[8])
            stream_temp[4] = 0
            stream_temp[7] = packet_list[0][9]
            stream_temp[8] = packet_list[0][10]
            #Write the CSV file for the normal files.
            with open(output_csv_dir + infect_input_file_list[infect_file_no - 1] + output_extension, 'ab+') \
                    as csv_file:
                csv_writer = csv.writer(csv_file, dialect='excel')
                csv_writer.writerow(stream_temp)
            num_tcp_stream += 1
    logger.info("Finish TCP CSV write, the sum of stream: " + str(num_tcp_stream))


def filter_infect_tcp_process(infect_file_no):
    global num_packet_label_infect
    global num_packet_label_normal
    logger.info("Start to process filter_tcp")

    process_infect_file = input_infect_dir + infect_input_file_list[infect_file_no - 1]
    print(process_infect_file)
    #process every line in the normal
    num_txt_line = 0
    output = open(process_infect_file + "_tcp.txt", 'w+')
    for txt_line in open(process_infect_file):
        logger.info("Process the txt line: " + str(num_txt_line))
        num_txt_line += 1
        txt_array = txt_line.split()
        if 7 > len(txt_array):
            continue
            #TCP 6 UDP 17
            #if not UDP, SET udp size AS 0
        if txt_array[2] == '6':
            output.writelines(txt_line)

    logger.info("Finish TCP filter ")
    output.close()


def filter_normal_tcp_process(normal_file_no):
    global num_packet_label_infect
    global num_packet_label_normal
    logger.info("Start to process filter_tcp")

    process_normal_file = input_normal_dir + normal_input_file_list[normal_file_no - 1]
    print(process_normal_file)
    #process every line in the normal
    num_txt_line = 0
    output = open(process_normal_file + "_tcp.txt", 'w+')
    for txt_line in open(process_normal_file):
        logger.info("Process the txt line: " + str(num_txt_line))
        num_txt_line += 1
        txt_array = txt_line.split()
        if 7 > len(txt_array):
            continue
            #TCP 6 UDP 17
            #if not UDP, SET udp size AS 0
        if txt_array[2] == '6':
            output.writelines(txt_line)

    logger.info("Finish TCP filter ")
    output.close()

####################################################
##########The main interactive of the Data Process
####################################################
show_help_info()
exitFlag = 0
while 1:
    #获得用户输入
    userInput = raw_input("Please Enter your Choice:")
    if userInput == '0':
        print("Scanning...")
        scan_input_data()
        print("Scanning finished...")
    elif userInput == '1':
        show_scan_result(1)
        process_normal_no = raw_input("Please Input which file you want to process:")
        print("Proceing Normal files...")
        normal_process(int(process_normal_no))
        print("Proceing Normal files Finished")
        print("The DB records has: " + str(normal_db_size))
    elif userInput == '2':
        show_scan_result(0)
        process_normal_no = raw_input("Please Input which file you want to process:")
        print("Proceing Infect files...")
        infect_process(int(process_normal_no))
        print("Proceing Infect files Finished")
    elif userInput == '3':
        print("Showing Help Information...")
        show_help_info()
    elif userInput == '4':
        show_scan_result(1)
        process_normal_no = raw_input("Please Input which file you want to process:")
        print("Proceing Normal files...")
        filter_normal_tcp_process(int(process_normal_no))
        print("Proceing Normal files Finished")
    elif userInput == '5':
        show_scan_result(0)
        process_normal_no = raw_input("Please Input which file you want to process:")
        print("Proceing Infect files...")
        filter_infect_tcp_process(int(process_normal_no))
        print("Proceing Infect files Finished")
    elif userInput == '9':
        print("Exit...")
        exitFlag = 1
    else:
        print("Not Valid Input, Please Try Again...")
        show_help_info()
    #Quit the programme
    if exitFlag == 1:
        #  ch.release()
        #  fh.release()
        break









