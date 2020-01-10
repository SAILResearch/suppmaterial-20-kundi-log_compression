"""
This script compares the size of static and dynamic information in parsed log files
"""
import pandas as pd
import ast
import sys
import os
import shutil
import LogPai_Drain

class CompareStaticDynamic:
    def __init__(self, file=None, settings=None):
        if file:
            self.file = file
            self.df = self.load_file(file)
        elif settings:
            # dataframe will be added after parse() is called
            self.settings = settings
            self.file = settings['file_path']

    def load_file(self, file):
        return pd.read_csv(file, low_memory=False)

    def compare(self):
        """
        Compare the size of static/dynamic information
        :return:
        """
        # Process templates and variables
        print('Comparing the size of static & dynamic information in log file: %s' % self.file)
        self.df['EventTemplateClean'] = self.df.apply(self.remove_wildcard, axis=1)
        self.df['DynamicClean'] = self.df.apply(self.concate_list, axis=1)

        # Read size
        static_size = self.sizeof_column(self.df['EventTemplateClean'])
        dynamic_size = self.sizeof_column(self.df['DynamicClean'])
        stat_vs_dyna_ratio = round(static_size/dynamic_size, 2)

        print('The static information of file: %s is %s' % (os.path.basename(self.file), self.sizeof_fmt(static_size)))
        print('The dynamic information of file: %s is %s' % (os.path.basename(self.file), self.sizeof_fmt(dynamic_size)))
        print('The static vs dynamic ratio of file: %s is %s' % (os.path.basename(self.file), str(stat_vs_dyna_ratio)))

    def sizeof_column(self, col):
        """ Calculate the size of a column"""
        # Convert col to text
        temp_text = '\n'.join([x for x in col])
        return sys.getsizeof(temp_text)

    def sizeof_fmt(self, num, suffix='B'):
        """
        Convert size to human readable format
        Ref: https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        :param num:
        :param suffix:
        :return:
        """
        for unit in ['B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Y', suffix)

    def remove_wildcard(self, row):
        return row['EventTemplate'].replace('<*>', '')

    def concate_list(self, row):
        row_content = row['ParameterList']
        if isinstance(row_content, list):
            return ''.join(row_content)
        else:
            return ''.join(ast.literal_eval(row_content))

    def parse(self, save_df=True):

        output_dir = os.path.sep.join(['../temp/ParseResult', os.path.basename(self.file).split('.')[0]])

        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir)

        os.makedirs(output_dir)

        logparser = LogPai_Drain.LogParser(log_format=self.settings['log_format'],
                               indir=os.path.dirname(self.file),
                               outdir=output_dir,
                               depth=self.settings['depth'],
                               st=self.settings['st'],
                               rex=self.settings['regex'])

        logparser.parse(os.path.basename(self.file))

        if save_df:
            self.df = logparser.df_log


if __name__ == '__main__':
    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        raise FileNotFoundError('File %s not found' % file_path)
    comp = CompareStaticDynamic(file_path)
    comp.compare()