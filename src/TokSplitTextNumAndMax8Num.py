import sys
import nltk
import os
from itertools import islice

replace_dic = {' ': '<spa>', '\t': '<tab>'}


def getMaxEightNumLimit(s):
    if not s.isdigit():
        return [s]
    else:
        # If this is all digits
        if not len(list(s)) > 8:
            # If length lower than 8 characters, we don't split
            return [s]
        else:
            temp_len = len(s)
            temp_digit_list = []
            for i in range(0, int(temp_len / 8)):
                temp_digit_list.append(s[i * 8:(i + 1) * 8])

            # If there are remaining characters
            if int(temp_len % 8) > 0:
                temp_digit_list.append(s[-int(temp_len % 8):])

            return temp_digit_list


def splitTextAndNum(s):
    temp_list = []

    temp_str = ''

    str_list = list(s)

    if len(str_list) == 1:
        return [s]

    for i in range(0,len(str_list)-1):

        x = str_list[i]
        x_next = str_list[i+1]

        temp_str += x

        if x.isdigit() != x_next.isdigit():
            # If current and next string not the same
            list_to_max_eight = getMaxEightNumLimit(temp_str)
            temp_list += list_to_max_eight
            temp_str = ''

    if not temp_str == '':

        if temp_str[-1].isdigit() != s[-1].isdigit():
            list_to_max_eight = getMaxEightNumLimit(temp_str)
            temp_list += list_to_max_eight
            temp_list.append(s[-1])
        else:
            temp_str += s[-1]
            list_to_max_eight = getMaxEightNumLimit(temp_str)
            temp_list += list_to_max_eight

    return temp_list


for line in sys.stdin:
    piece = line
        # Split by symbols, keep space
    tokenizer = nltk.tokenize.RegexpTokenizer("[^A-Za-z0-9]|[A-Za-z0-9]+")

    piece_array = list(tokenizer.tokenize(piece.lower()))

    # Preprocess, if a string size > 8, we split it

    piece_array_new = []

    for p_str in piece_array:
        piece_array_new += splitTextAndNum(p_str)

    print(' '.join([replace_dic.get(n, n) for n in piece_array_new]), end=' ')






