from enum import Enum
import subprocess
import shutil
import re
import os
import sys
import time
import psutil as ps
from datetime import datetime
import csv
from multiprocessing import Process, Queue, Manager
from multiprocessing.pool import ThreadPool


class runCompress:

    def __init__(self, file_path, repeat_file_list, compressor, isCompLevel, slicing_time=0.01):

        self.root_cwd = os.getcwd()
        # Check if file exists
        if not os.path.exists(file_path):
            print('[ERROR] File: %s not exist' % file_path)

        self.file_name = str(file_path).split(os.path.sep)[-1]

        self.slicing_time = slicing_time

        self.repeat_file_list = repeat_file_list

        self._createTestInSubFolder(compressor=compressor, file_path=file_path)

        self.compressor = compressor

        self.is_comp_lv = isCompLevel

        if isCompLevel:
            self.lv_list = range(1, 10, 1)
            self._generateCompressCommand_lv(compressor=self.compressor, file_name=self.file_name)

        else:
            if len(repeat_file_list) > 1:
                self._generateCompressShell(compressor=self.compressor, file_name=self.file_name,
                                            repeat_file_list=self.repeat_file_list)

            self._generateCompressCommand(compressor=self.compressor, file_name=self.file_name)


    def _createTestInSubFolder(self, compressor, file_path):
        """
        Create a seperate data in sub-folder, to avoid interference on changing target files from compressors
        :param compressor:
        :param file_name:
        :return:
        """
        # set current working directory

        os.chdir(os.path.dirname(file_path))

        # check if directory exists
        if not os.path.isdir(compressor):
            os.makedirs(compressor)

        shutil.copy(self.file_name, os.path.join(compressor, self.file_name))

        for i in range(0, len(self.repeat_file_list)):
            shutil.copy(self.file_name+"_%s"%str(i), os.path.join(compressor, self.file_name+"_%s"%str(i)))

        os.chdir(compressor)

    def _generateCompressShell(self, compressor, file_name, repeat_file_list):
        """
        Generate compress/decompress in a shell script
        """

        shell_content_comp = ''
        shell_content_decomp = ''
        shell_content_clean_comp = ''
        shell_content_clean_decomp = ''
        for each_repeat_file in repeat_file_list:
            each_repeat_file = os.path.basename(each_repeat_file)

            clean_compress_cmd = ''
            clean_decompress_cmd = ''
            # gzip
            if compressor == Compressors.GZIP.value:
                file_name_compressed = "%s.gz" % each_repeat_file
                compress_cmd = 'gzip %s' % each_repeat_file
                decompress_cmd = 'gzip -d %s' % file_name_compressed
            elif compressor == Compressors.BZIP2.value:
                file_name_compressed = "%s.bz2" % each_repeat_file
                compress_cmd = 'bzip2 %s' % each_repeat_file
                decompress_cmd = 'bzip2 -d %s' % file_name_compressed
            elif compressor == Compressors.SEVENZIP_PPMD.value:
                file_name_compressed = "%s.7z" % each_repeat_file
                compress_cmd = '7z a -m0=PPMD %s %s' % \
                               (file_name_compressed, each_repeat_file)
                decompress_cmd = '7z x -m0=PPMD %s %s' % \
                                 (file_name_compressed, each_repeat_file)
                clean_compress_cmd = 'rm %s' % each_repeat_file
                clean_decompress_cmd = 'rm %s' % file_name_compressed

            shell_content_comp += compress_cmd + '\n'
            shell_content_decomp += decompress_cmd + '\n'

            if clean_compress_cmd != '':
                shell_content_clean_comp += clean_compress_cmd + '\n'
            if clean_decompress_cmd != '':
                shell_content_clean_decomp += clean_decompress_cmd + '\n'

        tmp_name = repeat_file_list[0].split(os.path.sep)[1].split(".")[0] + compressor
        print(os.getcwd())

        self.shell_comp = tmp_name + '_comp.sh'
        self.shell_decomp = tmp_name + '_decomp.sh'

        self.shell_clean_comp = ''
        self.shell_clean_decomp = ''
        # print("../../tmp_shell/%s" % self.shell_comp)
        with open(self.shell_comp, 'w') as w_comp:
            w_comp.write(shell_content_comp)
        w_comp.close()

        with open(self.shell_decomp, 'w') as w_decomp:
            w_decomp.write(shell_content_decomp)
        w_decomp.close()

        if shell_content_clean_comp != '':
            self.shell_clean_comp = tmp_name + '_comp_clean.sh'
            with open(self.shell_clean_comp, 'w') as w_clean_comp:
                w_clean_comp.write(shell_content_clean_comp)
            w_clean_comp.close()

        if shell_content_clean_decomp != '':
            self.shell_clean_decomp = tmp_name + '_decomp_clean.sh'
            with open(self.shell_clean_decomp, 'w') as w_clean_decomp:
                w_clean_decomp.write(shell_content_clean_decomp)
            w_clean_decomp.close()
        # gzip
        if compressor == Compressors.GZIP.value:
            self.file_name_compressed = "%s.gz" % file_name
            self.compress_cmd = 'gzip %s' % file_name
            self.decompress_cmd = 'gzip -d %s' % self.file_name_compressed
        elif compressor == Compressors.BZIP2.value:
            self.file_name_compressed = "%s.bz2" % file_name
            self.compress_cmd = 'bzip2 %s' % file_name
            self.decompress_cmd = 'bzip2 -d %s' % self.file_name_compressed
        elif compressor == Compressors.SEVENZIP_PPMD.value:
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd = '7z a -m0=PPMD %s %s&&rm %s' % \
                                (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = '7z x -m0=PPMD %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)

    def _generateCompressCommand_lv(self, compressor, file_name):
        """
        Generate compress and decompress commands list to specify different levels
        :param compressor:
        :param file_name:
        :return:
        """
        # GZIP:
        if compressor == Compressors_SetLevels.GZIP.value:
            self.file_name_compressed = '%s.gz' % file_name
            self.compress_cmd_list = ['gzip -%s %s' % (str(lv), file_name) for lv in self.lv_list]
            self.decompress_cmd = 'gzip -d %s' % self.file_name_compressed

        # BZIP2:
        if compressor == Compressors_SetLevels.BZIP2.value:
            self.file_name_compressed = "%s.bz2" % file_name
            self.compress_cmd_list = ['bzip2 -%s %s' % (str(lv), file_name) for lv in self.lv_list]
            self.decompress_cmd = 'bzip2 -d %s' % self.file_name_compressed

        # PPMd:
        if compressor == Compressors_SetLevels.SEVENZIP_PPMD.value:
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd_list = ["7z a -m0=PPMd -mx=%s %s %s&&rm %s" %
                                      (str(lv), self.file_name_compressed, file_name, file_name) for lv in self.lv_list]
            self.decompress_cmd = '7z x -m0=PPMD %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)

    def _generateCompressCommand(self, compressor, file_name):
        """
        Generate compress and decompress commands;
        Future work may consider replace this part with a switch statement
        :param compressor:
        :return: None
        """

        # gzip
        if compressor == Compressors.GZIP.value:
            self.file_name_compressed = "%s.gz" % file_name
            self.compress_cmd = 'gzip %s' % file_name
            self.decompress_cmd = 'gzip -d %s' % self.file_name_compressed
        elif compressor == Compressors.PIGZ.value:
            self.file_name_compressed = "%s.gz" % file_name
            self.compress_cmd = 'pigz %s' % file_name
            self.decompress_cmd = 'unpigz -d %s' % self.file_name_compressed
        elif compressor == Compressors.ZIP.value:
            # -m will remove original file after compression;
            # -o will overwrite existing file
            self.file_name_compressed = "%s.zip" % file_name
            self.compress_cmd = 'zip -m %s %s' % (self.file_name_compressed, file_name)
            self.decompress_cmd = 'unzip -o %s&&rm %s' % (self.file_name_compressed, self.file_name_compressed)
        elif compressor == Compressors.COMPRESS.value:
            # compress is used for compress file to a ".Z" file
            # uncompress.real is for decompress
            self.file_name_compressed = "%s.Z" % file_name
            self.compress_cmd = 'compress %s' % file_name
            self.decompress_cmd = 'uncompress.real %s' % self.file_name_compressed
        elif compressor == Compressors.LZ4.value:
            self.file_name_compressed = "%s.lz4" % file_name
            self.compress_cmd = 'lz4 --rm %s' % file_name
            self.decompress_cmd = 'unlz4 --rm %s' % self.file_name_compressed
        elif compressor == Compressors.SEVENZIP_LZMA.value:
            # a: add to archive; x: extract from archive
            # Example: 7z a -m0=LZMA 1.txt.7z 1.txt
            #           7z x -m0=LZMA 1.txt.7z 1.txt
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd = '7z a -m0=LZMA %s %s&&rm %s' % \
                                (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = '7z x -m0=LZMA %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.SEVENZIP_LZMA2.value:
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd = '7z a -m0=LZMA2 %s %s&&rm %s' % \
                                (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = '7z x -m0=LZMA2 %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.SEVENZIP_BZIP2.value:
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd = '7z a -m0=BZIP2 %s %s&&rm %s' % \
                                (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = '7z x -m0=BZIP2 %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.SEVENZIP_DEFLATE.value:
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd = '7z a -m0=DEFLATE %s %s&&rm %s' % \
                                (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = '7z x -m0=DEFLATE %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.SEVENZIP_PPMD.value:
            self.file_name_compressed = "%s.7z" % file_name
            self.compress_cmd = '7z a -m0=PPMD %s %s&&rm %s' % \
                                (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = '7z x -m0=PPMD %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.SRANK.value:
            # Command: srank [ options ] file [options ] file...
            # Compressed files have suffix ".sr" added to file name
            # Files with suffix ".sr" are automatically expanded
            # The input file is not deleted
            self.file_name_compressed = "%s.sr" % file_name
            # After compress, we delete original file
            self.compress_cmd = 'srank %s&&rm %s' % (file_name, file_name)
            # After decompress, a "a.txt.n" file will be generated;
            # first we remove the file "a.txt.sr", we rename "a.txt.n" to "a.txt"
            self.decompress_cmd = 'srank %s&&rm %s&&mv %s.n %s' % \
                                  (self.file_name_compressed, self.file_name_compressed, file_name, file_name)
        elif compressor == Compressors.SR2.value:
            # To compress: sr2 input output
            # Remaining file won't be deleted
            self.file_name_compressed = "%s.sr2" % file_name
            self.compress_cmd = 'sr2 %s %s&&rm %s' % (file_name, self.file_name_compressed, file_name)
            self.decompress_cmd = 'sr2 %s %s&&rm %s' % (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.BZIP2.value:
            self.file_name_compressed = "%s.bz2" % file_name
            self.compress_cmd = 'bzip2 %s' % file_name
            self.decompress_cmd = 'bzip2 -d %s' % self.file_name_compressed
        elif compressor == Compressors.OCAMYD.value:
            # ocamyd [-<switch 1>] [-<switch 2>] <infile> <outfile>
            # Ocamyd is a file (de-)compressor based on Gordon V. Cormack's
            # Dynamic Markov Coding (DMC) algorithm.
            # Encoding example: ocamyd -s0 -m1 myfile.ext myfile.ext.oca
            # Decoding example: ocamyd -d myfile.ext.oca myfile.ext
            # switch:
            #       s: speed mode [0-3]
            #           s0: slowest (DMC+PPM+MATCH)
            #           s1: slow (DMC+PPM)
            #           s2: fast (DMC)
            #           s3: fastest (HITCACHE+DMC) (default)
            #       m: Memory usage [0(default)-9]: 64Mb to 900Mb
            #       d: Decodes <infile> to <outfile>

            # Here we use s2 (DMC)
            self.file_name_compressed = '%s.oca' % file_name
            self.compress_cmd = 'ocamyd -s2 %s %s&&rm %s' % \
                                (file_name, self.file_name_compressed, file_name)
            # d for decodes
            self.decompress_cmd = 'ocamyd -ds2 %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.QUICKLZ.value:
            self.file_name_compressed = "%s.qklz" % file_name
            self.compress_cmd = 'quicklz_compress %s %s&&rm %s' % \
                                (file_name, self.file_name_compressed, file_name)
            self.decompress_cmd = 'quicklz_decompress %s %s &&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.SZIP.value:
            # Compress: szip input output
            # Decompress: szip -d input
            self.file_name_compressed = '%s.sz' % file_name
            self.compress_cmd = 'szip %s %s&&rm %s' % \
                                (file_name, self.file_name_compressed, file_name)
            self.decompress_cmd = 'szip -d %s %s&&rm %s' % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        # elif compressor == Compressors.PAQ8PX.value:
        #     # Example (-3 switch: 1-9 is fast to best comp ratio; -d switch: decompress):
        #     # paq8px -3 Charlotte.txt
        #     # paq8px -d Charlotte.txt.paq8px171
        #     self.file_name_compressed = "%s.paq8px171" % file_name
        #
        #     self.compress_cmd = 'paq8px -3 %s&&rm %s' % (file_name, file_name)
        #     self.decompress_cmd = 'paq8px -d %s&&rm %s' % \
        #                           (self.file_name_compressed, self.file_name_compressed)
        # elif compressor == Compressors.NANOZIP.value:
        #     # Example: nz a -cc Charlotte.txt
        #     # nz x -cc Charlotte.txt.nz Charlotte.txt
        #     self.file_name_compressed = "%s.nz" % file_name
        #     self.compress_cmd = "nz a -cc %s&&rm %s" % (file_name, file_name)
        #     self.decompress_cmd = "nz x -cc %s %s&&rm %s" % \
        #                           (self.file_name_compressed, file_name, self.file_name_compressed)
        elif compressor == Compressors.ZPAQ.value:
            # Example: zpaq a wiki.txt.zpaq wiki.txt
            #          zpaq x wiki.txt.zpaq
            # Use compression level 3 (middle, lv from 1-5 and default is 1 fastest)
            # Set threads number to 1, or it will compress in parallel
            self.file_name_compressed = "%s.zpaq" % file_name
            self.compress_cmd = "zpaq a %s %s -t1&&rm %s" % (self.file_name_compressed, file_name, file_name)
            self.decompress_cmd = "zpaq x %s -t1&&rm %s" % (self.file_name_compressed, self.file_name_compressed)
        elif compressor == Compressors.CTW.value:
            # Usage: ctw e/d/i [-options] <input_filename> [<output_filename>]
            # Where e = encode, d = decode and i = show file information
            self.file_name_compressed = "%s.ctw" % file_name
            self.compress_cmd = "ctw ey %s %s&&rm %s" % \
                                (file_name, self.file_name_compressed, file_name)
            self.decompress_cmd = "ctw dy %s %s&&rm %s" % \
                                  (self.file_name_compressed, file_name, self.file_name_compressed)
        else:
            print('[ERROR] Compressor %s not in out list!' % compressor)
            sys.exit(1)

    def splitCommandPipeLines(self, cmd):
        return str(cmd).split('&&')

    def cleanUp(self, cmds):
        """
        Clean up data, to remove or rename extra data
        :param cmds:
        :return:
        """
        # Clean up
        if len(cmds) > 1:
            for i in range(1, len(cmds)):

                file_path = cmds[i].split(" ")[1]

                if os.path.isfile(file_path):
                    subprocess.Popen(cmds[i], shell=True).wait()
        else:
            pass

    def getFileSize(self, file_name):

        # file_size_cmd = 'stat -c %s {f}'.format(f=file_name)
        file_size_cmd = "ls -la %s | awk '{print $5}'" % file_name

        proc = subprocess.Popen(file_size_cmd, stdout=subprocess.PIPE, shell=True)
        output = proc.stdout.read()
        try:
            proc.kill()

            # Remove non-numeric values from output
            output_value = int(re.sub(r"\D", "", str(output)))
        except OSError:
            pass

        return output_value

    def compress_or_decompress(self, is_compress, cmd_compress=''):

        cpu_proc_time_all = 0.0


        if is_compress:
            # Usually the cmd is '', unless we want to see different levels
            if cmd_compress == '':
                # If command consists multiple pipelines
                cmds = self.splitCommandPipeLines(self.compress_cmd)
            else:
                cmds = self.splitCommandPipeLines(cmd_compress)
        else:
            cmds = self.splitCommandPipeLines(self.decompress_cmd)


        # If not repeat, this is the only result
        # If repeat, since all files are same, this result indicates the original/compressed file size
        cpu_proc_time_all = self.getTimeFromTimeCommand(cmds[0].split(" "))
        self.cleanUp(cmds)

        if len(self.repeat_file_list) > 1:
            # If repeat
            if is_compress:
                self.getTimeFromTimeCommand(['bash', './%s' % self.shell_comp])
            else:
                self.getTimeFromTimeCommand(['bash', './%s' % self.shell_decomp])


            try:
                # Clean
                if is_compress:
                    # Remove generated chunk copies
                    if self.shell_clean_comp != '':
                        subprocess.check_call(['bash', './%s' % self.shell_clean_comp])
                else:
                    if self.shell_clean_decomp != '':
                        subprocess.check_call(['bash', './%s' % self.shell_clean_decomp])
            except AttributeError:
                # If no clean shell
                pass



        if cpu_proc_time_all == 0.0:
            # Zero cannot be denominator
            # Color:red + text + End
            print(
                '\033[91m' + '[ERROR] Process not running, or file size too small: compression/decompression time close to 0' + '\033[0m')
            print(cmds[0])
            print(
                '\033[91m' + 'Time for this compression practice will treated as 0' + '\033[0m')
            return cpu_proc_time_all

        else:
            print(cpu_proc_time_all)
            return cpu_proc_time_all



    def getTimeFromPSUtil(self, cmd_list):
        proc = subprocess.Popen(cmd_list)

        pid = proc.pid

        ps_obj = ps.Process(pid)

        cpu_time_list = []
        try:

            while ps.pid_exists(pid) and ps_obj.status() != ps.STATUS_ZOMBIE:
                cpu_time_list.append(ps_obj.cpu_times())
                time.sleep(0.01)

        except ProcessLookupError:
            pass
        except ps.ZombieProcess:
            print("Zombie Process %s detected, cause it finished running" % str(pid))
            pass

        proc.kill()

        if len(cpu_time_list) > 0:
            # If monitor process captured something
            cpu_time = cpu_time_list[-1]
            print("cpu_time:%s" % (str(cpu_time)))
            user_time = float(getattr(cpu_time, 'user'))
            sys_time = float(getattr(cpu_time, 'system'))

            try:
                child_sys_user = float(getattr(cpu_time, 'children_user'))
            except AttributeError:
                child_sys_user = 0.0

            try:
                child_sys_time = float(getattr(cpu_time, 'children_system'))
            except AttributeError:
                child_sys_time = 0.0

            cpu_proc_time_all = user_time + sys_time + child_sys_user + child_sys_time
        else:
            # Nothing captured
            cpu_proc_time_all = 0.0
        print(cpu_proc_time_all)


    def getTimeFromTimeCommand(self, cmd_list):

        cmd = 'time ' + ' '.join(cmd_list)

        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #output = proc.stderr.readlines()[0].decode('utf-8')
        output = proc.stderr.read().decode('utf-8')

        try:
            # Kill process
            proc.kill()
            # remove non-numeric characters
            print(output)

            re_groups = re.compile(r'(.*)user\s(.*)system\s*', re.M).search(output)

            user_time = float(re_groups.groups(0)[0])
            system_time = float(re_groups.groups(0)[1])

            cpu_proc_time_all = user_time + system_time
            return cpu_proc_time_all
        except TypeError as err:
            print(err)
        except OSError as e:
            pass


    def run(self):

        if self.is_comp_lv:

            # Build a list to restore all the dictionaries
            dict_list = []
            # If it's comparing different levels
            for compress_cmd in self.compress_cmd_list:
                orginal_file_size = self.getFileSize(self.file_name)

                original_file_size_mb = float(orginal_file_size / (1024 * 1024))

                compress_time = self.compress_or_decompress(is_compress=True, cmd_compress=compress_cmd)

                compressed_file_size = self.getFileSize(self.file_name_compressed)

                compressed_file_size_mb = float(compressed_file_size / (1024 * 1024))

                decompress_time = self.compress_or_decompress(is_compress=False)

                # Represent how many bits will one character takes to represent
                # Bit per character (aka. bpc)
                compression_ratio_bpc = round(float(compressed_file_size * 8 / orginal_file_size), 2)

                # default compression_speed and decompression_speed will be treated as 0
                compression_speed = 0.0
                decompress_speed = 0.0

                if compress_time > 0:
                    # Compression speed (Megabytes per second)
                    compression_speed = round(float(original_file_size_mb / compress_time), 2)

                if decompress_time > 0:
                    # Decompression speed (Megabytes per second)
                    decompress_speed = round(float(original_file_size_mb / decompress_time), 2)

                level = self.lv_list[self.compress_cmd_list.index(compress_cmd)]

                dict = {"FileName": self.file_name, "Compressor": self.compressor,
                        "OriginalFileSize": orginal_file_size, "CompressedFileSize": compressed_file_size,
                        "OriginalFileSizeMB": original_file_size_mb, "CompressedFileSizeMB": compressed_file_size_mb,
                        "CompressionRatioBPC": compression_ratio_bpc, "CompressionLevel": level,
                        "CompressTime": compress_time, "DecompressTime": decompress_time,
                        "CompressionSpeed": compression_speed, "DecompressionSpeed": decompress_speed}
                dict_list.append(dict)
            return dict_list


        else:
            # If it's running all compressors
            # Start running compressors

            orginal_file_size = self.getFileSize(self.file_name)
            print("orginal_file_size:%s" % str(orginal_file_size))

            original_file_size_mb = float(orginal_file_size / (1024 * 1024))

            compress_time = self.compress_or_decompress(is_compress=True)

            print("compress_time:%s" % str(compress_time))

            compressed_file_size = self.getFileSize(self.file_name_compressed)
            print("compressed_file_size:%s" % str(compressed_file_size))

            compressed_file_size_mb = float(compressed_file_size / (1024 * 1024))

            decompress_time = self.compress_or_decompress(is_compress=False)

            print("decompress_time:%s" % str(decompress_time))

            # Represent how many bits will one character takes to represent
            # Bit per character (aka. bpc)
            compression_ratio = round(float(compressed_file_size * 8 / orginal_file_size), 2)
            print("compression_ratio:%s" % str(compression_ratio))

            # default compression_speed and decompression_speed will be treated as 0
            compression_speed = 0.0
            decompress_speed = 0.0

            if compress_time > 0:
                # Compression speed (Megabytes per second)
                compression_speed = round(float(original_file_size_mb / compress_time), 2)
                print("compression_speed:%s" % str(compression_speed))

            if decompress_time > 0:
                # Decompression speed (Megabytes per second)
                decompress_speed = round(float(original_file_size_mb / decompress_time), 2)
                print("decompress_speed:%s" % str(decompress_speed))


            # Return a dictionary: file_name, compressor, compression_ratio, compress_time, decompress_time
            print('\033[91m' + 'End' + '\033[0m')
            return [{"FileName": self.file_name, "Compressor": self.compressor,
                     "OriginalFileSize": orginal_file_size, "CompressedFileSize": compressed_file_size,
                     "OriginalFileSizeMB": original_file_size_mb, "CompressedFileSizeMB": compressed_file_size_mb,
                     "CompressionRatio": compression_ratio, "CompressTime": compress_time,
                     "DecompressTime": decompress_time,
                     "CompressionSpeed": compression_speed, "DecompressionSpeed": decompress_speed}]


class Compressors(Enum):
    GZIP = 'gzip'
    PIGZ = 'pigz'
    ZIP = 'zip'
    COMPRESS = 'compress'
    LZ4 = 'lz4'
    SEVENZIP_LZMA = '7zip_lzma'
    SEVENZIP_LZMA2 = '7zip_lzma2'
    SEVENZIP_PPMD = '7zip_ppmd'
    SEVENZIP_BZIP2 = '7zip_bzip2'
    SEVENZIP_DEFLATE = '7zip_deflate'
    SRANK = 'srank'
    SR2 = 'sr2'
    BZIP2 = 'bzip2'
    OCAMYD = 'ocamyd'
    QUICKLZ = 'quicklz'
    SZIP = 'szip'
    ZPAQ = 'zpaq'
    CTW = 'ctw'


class Compressors_SetLevels(Enum):
    GZIP = 'gzip'
    BZIP2 = 'bzip2'
    SEVENZIP_PPMD = '7zip_ppmd'


