import subprocess
import sys
import os
import random
import shutil
import platform
import math
import statistics
from multiprocessing import Manager, Pool, cpu_count
import re
import csv
import tenfoldCrossEntropy
import Compress
import LogPai_Drain
# Import write lock
try:
    from readerwriterlock import rwlock
    lock = rwlock.RWLockWrite().gen_wlock()
except ImportError:
    from threading import Lock
    lock = Lock()


class TruncateLog:

    def __init__(self, file='', nsample=10, size_pow=None, settings=None, out_path = 'out.csv', threshold_file='../thresh/threshold.csv', from_gram=1, to_gram=10):
        self.file = file
        self.nsample = nsample
        self.size_pow = size_pow
        self.size_str = self._getSizeString(size_pow)
        self.settings = settings
        self.out_path = out_path
        self.threshold_file = threshold_file
        self.from_gram = from_gram
        self.to_gram = to_gram

    def _getSizeString(self, size):

        if size is None:
            # Size string return None
            # When parsing only, we do not consider the block sizes
            return None

        if platform.system() == 'Linux':
            if size < 10:
                size_str = str(int(math.pow(2, size))) + 'K'
            elif 10 <= size < 20:
                size_str = str(int(math.pow(2, size - 10))) + 'M'

        elif platform.system() == 'Darwin':
            size_str = str(int(math.pow(2, size)) * 1024)

        print('Processing log %s with block size: %s' % (self.file, size_str))
        return size_str

    def getTotalLines(self):
        """Get total number of lines of a text file"""
        proc = subprocess.Popen("wc -l %s | awk '{print $1}'" % self.file, shell=True, stdout=subprocess.PIPE)
        output = str(proc.stdout.read())

        try:
            # Kill process
            proc.kill()
            # remove non-numeric characters
            total_lines = int(re.sub(r"\D", "", str(output)))
            return total_lines
        except TypeError:
            print('[ERROR] Cannot access a valid line count number from file: %s; the output is: %s' % (
            self.file, output))
            sys.exit(1)
        except OSError:
            pass

    def generateTruncateFile(self, start, end, file_name, idx, isEntropy, repeat=1):
        """Generate a log file after truncate to a specific sample"""

        temp_dir = os.path.join('../temp', os.path.basename(self.file).split('.')[0])

        if not os.path.exists(os.path.abspath(temp_dir)):
            os.makedirs(os.path.abspath(temp_dir))

        # Save a new name according to different log file types

        file_name_pure = str(file_name).split(os.path.sep)[-1]

        # Distinguish files
        dist = 'E' if isEntropy else 'C'

        if str(file_name).endswith('.log'):
            new_file_name = '%s/%s_%s%s_%s.log' % (temp_dir, dist, file_name_pure.split('.log')[0], str(self.size_str), idx)
        elif str(file_name).endswith('.txt'):
            new_file_name = '%s/%s_%s%s_%s.txt' % (temp_dir, dist, str(file_name_pure).split('.txt')[0], str(self.size_str), idx)
        else:
            new_file_name = '%s/%s_%s%s_%s' % (temp_dir, dist, str(file_name_pure), str(self.size_str), idx)

        if not isEntropy:

            tmp_cp_list = []
            # If file already exist, skip the following steps
            if not os.path.isfile(new_file_name):

                cmd = "cat %s | sed -n '%s, %sp' | head -c %s >%s" % \
                      (file_name, start, end, str(self.size_str), new_file_name)

                print(cmd)

                proc = subprocess.Popen(cmd, shell=True)
                proc.wait()
                try:
                    proc.kill()
                except OSError:
                    pass
            if repeat > 1:

                for i in range(0, repeat):
                    cmd_cp = "cp %s %s" % (new_file_name, new_file_name + "_" + str(i))

                    proc = subprocess.Popen(cmd_cp, shell=True)
                    proc.wait()
                    try:
                        proc.kill()
                    except OSError:
                        pass

                    tmp_cp_list.append(new_file_name + "_" + str(i))

            return new_file_name, tmp_cp_list

        else:
            # If measuring entropy, create new files anyways
            # Since we need to know the number of tokens & characters
            cmd = "cat %s | sed -n '%s, %sp' | head -c %s > %s_temp" % (file_name, start, end, str(self.size_str), new_file_name)
            subprocess.Popen(cmd, shell=True).wait()
            # Calculate #characters in log block
            num_chars = subprocess.check_output("wc -c %s_temp | awk '{print $1}'" % new_file_name, shell=True).decode('utf-8').strip()
            cmd = "cat %s_temp | python3 Tokenizer.py > %s && rm %s_temp" % (new_file_name, new_file_name, new_file_name)
            subprocess.Popen(cmd, shell=True).wait()
            # Calculate #tokens
            num_tokens = subprocess.check_output("wc -w %s | awk '{print $1}'" % new_file_name, shell=True).decode('utf-8').strip()

            bpt_bpc_ratio = float(num_tokens)/float(num_chars)

            return new_file_name, bpt_bpc_ratio



    def getUpperBound(self, total_lines):
        """
        Get max allowed upper bound
        """
        get_bound_cmd = 'tail -c %s %s | wc -l' % (self.size_str, self.file)

        proc = subprocess.Popen(get_bound_cmd, shell=True, stdout=subprocess.PIPE)
        output = str(proc.stdout.read())

        try:
            # Kill process
            proc.kill()
            # remove non-numeric characters
            bound_counts = int(re.sub(r"\D", "", str(output)))

            if bound_counts == total_lines:
                print('[WARN] The size of file %s is less than or equal to your cutoff threshold. Please check original file size! ' % self.file)

            return total_lines-bound_counts

        except TypeError:
            print('[ERROR] Cannot access a valid boundary line count number from file: %s; the output is: %s' % (
                self.file, output))
            sys.exit(1)
        except OSError:
            pass

    def parse(self):

        setting = self.settings

        output_dir = os.path.sep.join([os.path.realpath('.'), '../temp', os.path.basename(setting['file_path']).split('.')[0]])
        log_path = setting['file_path']

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

        os.makedirs(output_dir)

        logparser = LogPai_Drain.LogParser(log_format=setting['log_format'],
                               indir=os.path.dirname(log_path),
                               outdir=output_dir,
                               depth=setting['depth'],
                               st=setting['st'],
                               rex=setting['regex'])

        logparser.parse(os.path.basename(log_path))

    def UpdateRepeat(self, compressor, tup_list):
        """
        Decide how many times the compression/decompression should be repeated
        This is a simple example. You can customize your own rules to calculate the number of repetitions.
        :param compressor:
        :param tup_list:
        :return:
        """

        if 'access' in self.file.lower():
            file_name = "AccessLog"
        elif 'firewall' in self.file.lower():
            file_name = "FirewallLog"
        elif 'gutenberg' in self.file.lower():
            file_name = "Gutenberg"
        elif 'hdfs' in self.file.lower():
            file_name = "HDFS"
        elif 'linuxsys' in self.file.lower():
            file_name = "LinuxSysLog"
        elif 'thunderbird' in self.file.lower():
            file_name = "Thunderbird"
        elif 'wiki' in self.file.lower():
            file_name = "Wiki"
        elif 'liberty' in self.file.lower():
            file_name = "Liberty"
        elif 'spark' in self.file.lower():
            file_name = "Spark"
        elif 'spirit' in self.file.lower():
            file_name = "Spirit"
        elif 'windows' in self.file.lower():
            file_name = "Windows"
        else:
            raise FileNotFoundError("File %s not in the list" % self.file)

        if compressor.value == 'gzip':
            comp_algo = 'LZ77'
        elif compressor.value == 'bzip2':
            comp_algo = 'BWT'
        elif compressor.value == '7zip_ppmd':
            comp_algo = 'PPMD'

        for tup in tup_list:

            if file_name == tup[0] and comp_algo == tup[1]:

                # If between 1k to 512K:
                if self.size_pow < 10:
                    if comp_algo == 'PPMD' or comp_algo == "BWT":
                        return 10*(20-int(self.size_pow))
                    else:
                        # LZ77
                        return 100*(20-int(self.size_pow))
                elif self.size_pow < 17:
                    # If 1M to 64M
                    if comp_algo == 'PPMD' or comp_algo == "BWT":
                        return 1*(20-int(self.size_pow))
                    else:
                        # LZ77
                        return 10*(20-int(self.size_pow))
                else:
                    # If > 128M
                    return 1

        print("FileName:%s, Compression algorithm:%s not found" % (self.file, compressor.value))
        sys.exit(1)

    def run(self, output_file_path, isEntropy, isCompress, isSetCompressLevel, isParseLog):
        total_line_count = self.getTotalLines()

        # Percentage
        lower_bound = 0
        upper_bound = self.getUpperBound(total_line_count)

        # Set seed
        random.seed(1)

        # Create thread pool
        # Use half of the available cpus
        p = Pool(cpu_count()//2)
        manager = Manager()
        queue = manager.Queue()

        temp_file_list = []

        if isEntropy:
            # Entropy
            # Stores all bpt to bpc ratios
            ratio_list = []

            for i in range(0, self.nsample):
                random_num = random.randint(lower_bound, upper_bound)

                start = 1 if upper_bound ==0 else random_num
                end = total_line_count

                generated_file, bpt_to_bpc_ratio = self.generateTruncateFile(start, end, self.file, i, True)

                temp_file_list.append(generated_file)
                ratio_list.append(bpt_to_bpc_ratio)

                p.apply_async(self.start_parallel_entropy, args=(generated_file, ratio_list, self.from_gram, self.to_gram, output_file_path, self.size_str, queue, ))

        if isCompress:

            tup_list = self.read_threshold(self.threshold_file)

            if isSetCompressLevel:
                CompressorsEnum = Compress.Compressors_SetLevels
            else:
                CompressorsEnum = Compress.Compressors

            #Compressors
            for compressor in CompressorsEnum:

                # If threshold file not provided, set to 1 by default
                repeat = 1

                if tup_list is not None and not isSetCompressLevel:
                    # Repeat X times to capture the compression/decompression speed of small files
                    try:
                        repeat = self.UpdateRepeat(compressor, tup_list)
                    except UnboundLocalError:
                        # If not defined
                        pass

                for i in range(0, self.nsample):
                    random_num = random.randint(lower_bound, upper_bound)

                    start = 1 if upper_bound == 0 else random_num
                    end = total_line_count

                    generated_file, tmp_cp_list = self.generateTruncateFile(start, end, self.file, i, False, repeat)

                    if len(tmp_cp_list) > 0:
                        # If repeat files are generated
                        temp_file_list = temp_file_list + tmp_cp_list

                    temp_file_list.append(generated_file)

                    p.apply_async(self.start_parallel_compress, args=(generated_file, tmp_cp_list, compressor.value, isSetCompressLevel, queue, ))

        p.close()
        p.join()
        dict_list = []
        while not queue.empty():
            dict_list.append(queue.get())

        # Write output to csv

        # Colnames
        col_names = sorted(dict_list[0].keys())

        with lock:
            if not os.path.isfile(self.out_path):
                # If not exist, create with headers
                with open(self.out_path, 'w') as w:
                    dict_writer = csv.DictWriter(w, col_names)
                    dict_writer.writeheader()
                    dict_writer.writerows(dict_list)
                w.close()
            else:
                # If exist, just append
                with open(self.out_path, 'a') as w:
                    dict_writer = csv.DictWriter(w, col_names)
                    dict_writer.writerows(dict_list)
                w.close()

        # Remove temp files
        for temp_file in temp_file_list:
            temp_file = os.path.abspath(temp_file)
            if os.path.exists(temp_file):

                os.remove(temp_file)

    def read_threshold(self, file):
        """
        Read threshold file to a list of tuples
        The threshold file records still from which size+compressor, will compression time be captured correctly
        :param file:
        :return: tupList: a list of tuple
        """
        if not os.path.isfile(file):
            return None

        reader = csv.reader(open(file, "r"), delimiter=",")
        headers = next(reader, None)
        tupList = []

        for row in reader:
            f_name = str(row[0])
            comp_name = str(row[1])
            pow_num = int(row[2])
            tup = (f_name, comp_name, pow_num)
            tupList.append(tup)
        return tupList

    def start_parallel_entropy(self, processed_file, ratio_list, gram_lower, gram_higher, out_dir, size_str, queue):
        # Entropy
        entropy_gram_dict = tenfoldCrossEntropy.run_ten_fold(processed_file, gram_lower, gram_higher, out_dir)

        for gram, entropy_list_bpt in entropy_gram_dict.items():

            entropy_list = []

            for entro, ratio in zip(entropy_list_bpt, ratio_list):
                if entro == 'NA':
                    continue
                else:
                    entropy_list.append(entro * ratio)

            # Entropy bpc
            mean_entropy = statistics.mean(entropy_list)

            result_dic = {'FileName': str(os.path.basename(processed_file)), 'Entropy': str(mean_entropy), 'Size': size_str, 'Gram': gram}

            queue.put(result_dic)

        return result_dic

    def start_parallel_compress(self, file_path, repeat_file_list, compressor, isCompLevel, queue):
        run_compress_obj = Compress.runCompress(file_path, repeat_file_list, compressor, isCompLevel)
        result_dic_list = run_compress_obj.run()

        if os.getcwd() != run_compress_obj.root_cwd:
            os.chdir(run_compress_obj.root_cwd)

        for result_dic in result_dic_list:
            print(result_dic)

            queue.put(result_dic)

        return result_dic_list


