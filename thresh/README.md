# Threshold file

When evaluating the CPU time used for compression and decompression, we realized that it was difficult to capture the precise time taken to compress/decompress small files (e.g., less than one second). 
Thus, we repeated the process of compressing/decompressing small files multiple times and measure the total time taken for these repetitions.
Then, we calculated the average time taken for each repetition.

For example, in our experimental environment, the compression time of LZ77 compressor on HDFS log blocks exceeds a time threshold (customizable, we use 1 second here) at 256Mb (2^18Kb) or larger chunk sizes.
The blocks which has a lower than 256Mb size will be copied and compressed/decompressed repeatedly. 
We put the following information into the threshold file.


|FileName|Compressor|Pow|
| :-----:| :------: | :-----:|
| HDFS   | LZ77     | 18 |


Repetitions will be implemented only if threshold.csv file exists. 
 
