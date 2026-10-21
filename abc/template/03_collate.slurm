#!/bin/bash

#SBATCH --partition="sapphire"
#SBATCH --parsable
#SBATCH -o batch-output.log
#SBATCH --open-mode=append

echo "this is the collate script running on `hostname`";

module load GCC/11.3.0
module load OpenMPI/4.1.4
#module load r/3.6.2
module load foss/2022a R/4.2.2

#edit working dir for different task arrays on cluster (set your directory)
cd ~/outbreaksimulator/abc_output/${RUN_NAME}

# The job command(s):
time R --no-save < 03_collate.R