import os
import sys
import platform
os.chdir(os.path.realpath('.'))
from TruncateLog import TruncateLog
from Compare_Size_Static_Dynamic import CompareStaticDynamic


benchmark_settings = {
    # We used an industrial access log in our study. Therefore, we cannot provide it.
    'Firewall': {
        'log_file': '../logs/FirewallLog10M.log',
        'log_format': '<Date> <Time>  <Level> <IP>  :<Month> <Day> <Time2> <Component1> <Component2>: <Content>',
        'regex': [r'(\d+\.){3}\d+(/\d+)?'],
        'st': 0.5,
        'depth': 4
    },

    'HDFS': {
        'log_file': '../logs/HDFS10M.log',
        'log_format': '<Date> <Time> <Pid> <Level> <Component>: <Content>',
        'regex': [r'blk_-?\d+', r'(\d+\.){3}\d+(:\d+)?'],
        'st': 0.5,
        'depth': 4
        },

    'LinuxSyslog': {
        'log_file': '../logs/LinuxSysLog10M.log',
        'log_format': '<Month> <Date> <Time> <Level> <Component>(\[<PID>\])?: <Content>',
        'regex': [r'(\d+\.){3}\d+', r'\d{2}:\d{2}:\d{2}'],
        'st': 0.39,
        'depth': 6
    },

    'Thunderbird': {
        'log_file': '../logs/Thunderbird10M.log',
        'log_format': '<Label> <Timestamp> <Date> <User> <Month> <Day> <Time> <Location> <Component>(\[<PID>\])?: <Content>',
        'regex': [r'(\d+\.){3}\d+'],
        'st': 0.5,
        'depth': 4
        },

    'Liberty': {
        'log_file': '../logs/Liberty10M.log',
        'log_format': '- <Timestamp> <Date> <User> <Month> <Day> <Time> <Location> <Content>',
        'regex': [r'(\d+\.){3}\d+', r'0x.*?\s', r'IRQ(\d+) -> (\d+):(\d+)', r'(.*?): message-id=<(\d+)\.(.*?)@'],
        'st': 0.5,
        'depth': 4
    },

    'Spark': {
        'log_file': '../logs/Spark10M.log',
        'log_format': '<Date> <Time> <Level> <Component>: <Content>',
        'regex': [r'(\d+\.){3}\d+(:\d+)?'],
        'st': 0.5,
        'depth': 4
    },

    'Spirit': {
        'log_file': '../logs/Spirit10M.log',
        'log_format': '<Label> <TimeStamp> <Date> <User> <Month> <Day> <Time> <UserGroup> <Component>(\[<PID>\])?(:)? <Content>',
        'regex': [r'0x.*?\s', r'(\d+\.){3}\d+(:\d+)?', r'#(\d+)#', r'<(\d{14})\.(.*?)\@', r'(\d+)-(\d+)', r'(\d+)kB', r'\d{2}:\d{2}:\d{2}'],
        'st': 0.5,
        'depth': 4
    },

    'Windows': {
        'log_file': '../logs/Windows10M.log',
        'log_format': '<Date> <Time>, <Level>                  <Component>    <Content>',
        'regex': [r'0x.*?\s'],
        'st': 0.7,
        'depth': 5
    },

}


if __name__ == '__main__':

    # Check OS
    if platform.system() != 'Linux':
        raise SystemError('[ERROR] Unfortunately, only Linux system is supported in current version.')

    # Usage:
    # nsample: how many chunks you want here
    # size: how many Kb you want

    # Min size from 2^0 = 1Kb, to 2^19 = 512MB

    min = 0
    max = 19

    output_dir = '../res'
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    output_dir = os.path.abspath(output_dir)

    inp = str(sys.argv[1])

    # This file provides threshold for repetition.
    # If below this threshold, the file will be copied X times then compressed
    # Then we calculate the average compression/decompression time
    # This is used when compression/decompression time cannot be well-captured (for small-sized logs)
    # If such file is not provided, the file will not be repeated

    threshold_file = '../thresh/threshold.csv'

    # Shuffle the file?
    isEntropy = True
    isCompress = False
    isSetCompressLevel = False
    isParseLog = False

    if isSetCompressLevel:
        output_file_name = 'comp_lv.csv'
    elif isCompress:
        output_file_name = 'comp.csv'
    else:
        output_file_name = 'entropy.csv'

    out_path = os.path.join(output_dir, inp + '_' + output_file_name)

    # Clean if exist
    if os.path.isfile(out_path):
        os.remove(out_path)

    if isParseLog:

        if inp in benchmark_settings.keys():
            obj = CompareStaticDynamic(settings=benchmark_settings[inp])
            obj.parse()
            obj.compare()

        else:
            raise AttributeError('[ERROR] Wrong input, only the following inputs are supported:\n' + ','.join(benchmark_settings.keys()))

    else:

        file_path = os.path.abspath(benchmark_settings[inp].get('log_file'))

        for i in range(min, max+1):

            obj = TruncateLog(file=file_path, nsample=10, size_pow=i,
                              out_path=out_path, threshold_file=threshold_file,
                              from_gram=1, to_gram=10)

            obj.run(output_dir, isEntropy=isEntropy, isCompress=isCompress, isSetCompressLevel=isSetCompressLevel,
                    isParseLog=isParseLog)

