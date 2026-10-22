#!/bin/bash

#SBATCH --partition="sapphire"
#SBATCH --parsable
#SBATCH -o batch-output.log
#SBATCH --open-mode=append

echo "this is the init script running on `hostname`";

module --force purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

# Activate virtual environment
cd ~/outbreaksimulator
source venv/bin/activate

# Set working directory
cd ~/outbreaksimulator/abc_output/${RUN_NAME}

# The job command(s):
time python 01_init.py $RUN_NAME