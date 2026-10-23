#!/bin/bash

#SBATCH --partition="sapphire"
#SBATCH --parsable
#SBATCH -o batch-output.log
#SBATCH --open-mode=append

echo "this is the collate script running on `hostname`";

module --force purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

# Activate virtual environment
cd ~/outbreaksimulator
source venv/bin/activate

# The job command(s):
time python visualisation.py