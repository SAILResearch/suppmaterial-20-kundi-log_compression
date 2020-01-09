import sys
import subprocess
import shutil
import re
import math
import os


def calculate_cross_entropy(tokenized_file, gram_size):
    """
    Calculate the cross entropy of a text file using n-gram models, using a 10-fold cross validation.
    This function uses the KenLM language model implementation to build and query n-gram models.
    For creating the 10 folds for evaluation, this function splits a file into 10 equal-sized parts, without shuffling
    Input:
    - tokenized_file:
        a text file in which tokens (or characters) are separated by by any number of '\0', '\t' '\r', and ' '
    -gram_size:
        the gram size of the n-gram model used to calculate the entropy
    """

    if gram_size == 1:
        isUniGram = True
    else:
        isUniGram = False

    processed_file = tokenized_file
    # Split the processed file into 10 chunks: using the split command
    try:
        p_split = subprocess.check_call(['split', '-d', '-n', 'l/10', processed_file, processed_file + "_"])
    except subprocess.CalledProcessError as e:
        print("Failed to split the file into chunks.")

    entropy_values = []

    ## calculate the cross-entropy values
    for fold in range(0, 10):
        # train text
        train_chunks = [processed_file + "_0" + str(i) for i in range(0, 10) if i != fold]

        train_merged = processed_file + "_train_chunks_merged"

        with open(train_merged, 'wb') as merged_f:
            for one_chunk in train_chunks:
                with open(one_chunk, 'rb') as chunk_f:
                    shutil.copyfileobj(chunk_f, merged_f,
                                       1024 * 1024 * 10)  # 10MB per writing chunk to avoid huge memory usage

        # estimate n-gram model on training text
        try:

            if isUniGram:
                # Build 2 gram and query from it
                p_lmplz = subprocess.check_call(['lmplz', '-o', '2', '--discount_fallback', '-S', '6%', '--text',
                                                 train_merged, '--arpa', train_merged + '.arpa'])
            else:
                p_lmplz = subprocess.check_call(
                    ['lmplz', '-o', str(gram_size), '--discount_fallback', '-S', '6%', '--text',
                     train_merged, '--arpa', train_merged + '.arpa'])
                # build_binary bible.arpa bible.binary # change the format of the model for fast query
                p_build_binary = subprocess.check_call(
                    ['build_binary', train_merged + '.arpa', train_merged + '.binary'])

        except subprocess.CalledProcessError as e:
            print("Failed to estimate n-gram model.")
            print(e)

        # test text
        test_chunk = processed_file + "_0" + str(fold)

        try:
            if isUniGram:
                query_cmd = 'ngram -order 1 -lm %s.arpa -ppl %s >%s_prob' % (train_merged, test_chunk, test_chunk)
            else:
                query_cmd = 'query ' + train_merged + '.binary' + ' <' + test_chunk + ' >' + test_chunk + '_prob'
            p_query = subprocess.check_call(query_cmd, shell=True)
        except subprocess.CalledProcessError as e:
            print("Failed to query the probabilities.")
            print(e)

        # get the perplexity value from the querying results
        try:
            tail_cmd = 'tail -n 4 ' + test_chunk + '_prob'
            tail_string = subprocess.check_output(tail_cmd, shell=True).decode("utf-8")
            # print(tail_string)
        except subprocess.CalledProcessError as e:
            print(e)

        if isUniGram:
            p_perp = re.compile(r'ppl=\s*(\d+\.\d+)\s*', re.M)
        else:
            p_perp = re.compile(r'Perplexity including OOVs:\s*(\d+\.\d+)\s*', re.M)

        m_perp = p_perp.search(str(tail_string))

        try:
            perp = float(m_perp.group(1))
            print('Perplexity: ' + str(perp))
            entropy = math.log2(perp)
            print('Entropy: ' + str(entropy))
        except AttributeError as e:
            entropy = "NA"
            print('Entropy not available')
            print(tail_string)
            print(e)

        entropy_values.append(entropy)

        # remove the intermediate files
        if os.path.exists(train_merged):
            os.remove(train_merged)
        if os.path.exists(train_merged + '.arpa'):
            os.remove(train_merged + '.arpa')
        if os.path.exists(train_merged + '.binary'):
            os.remove(train_merged + '.binary')

    return entropy_values


def run_ten_fold(processed_file, gram_lower=2, gram_higher=10, out_dir=''):

    processed_file = os.path.abspath(processed_file)

    file_name = processed_file.split(os.path.sep)[-1].split('.')[0]

    entropy_gram_dict = {}


    # Grams
    for i in range(gram_lower, gram_higher + 1):

        if not os.path.isfile(processed_file):
            print('[ERROR] File path: %s doesn\'t exist' % processed_file)
            sys.exit(1)
        entropy_values = calculate_cross_entropy(processed_file, i)

        out = '=============================\n' \
              'File:%s\n' \
              'Gram:%d\n' \
              'EntropyValues:%s\n' % \
              (file_name, i, str(entropy_values))
        print(out)

        entropy_gram_dict[i] = entropy_values

    # Clean dataset
    for i in range(0, 10):
        splited_file_name = processed_file + "_0" + str(i)
        splited_file_prob_name = splited_file_name + "_prob"

        if os.path.exists(splited_file_name):
            os.remove(splited_file_name)
        if os.path.exists(splited_file_prob_name):
            os.remove(splited_file_prob_name)

    return entropy_gram_dict

