# Source code
This section is the implementation of our research work.

## Set-up
Before start, please make sure you pre-install the [compression & entropy analysis tools](../tools/README.md).

## Configurations
Define the following configurations in [main.py](main.py):
    
    - Setup block size range: 
        # block_size_pow_min: Minimum block size (2^Min Kb).  
        # block_size_pow_max: Maximum block size (2^Max Kb).
        # The above parameters should be set in range 0 to 19. Min block size should not exceed Max block size. 
        
    - Setup test scenario:
         # Entropy: isEntropy = True, others equal to False
         # Compression: isCompress = True, others equal to False
         # Compression levels: isCompress = True, isSetCompressLevel = True, others equal to False
         # Check Static vs Dynamic information: isParseLog = True, others equal to False

## Test
We use python3.6 as the default python version.

    python main.py ARGUMENT
   
 The ARGUMENT should be one of the following options:
 
    Firewall
    HDFS
    LinuxSyslog
    Thunderbird
    Liberty
    Spark
    Spirit
    Windows
    Gutenberg
    Wiki
    
