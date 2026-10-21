#!/bin/bash

#SBATCH --partition="sapphire"
#SBATCH --parsable
#SBATCH -o batch-output.log
#SBATCH --open-mode=append

echo "this is the init script running on `hostname`";

module load foss/2022a R/4.2.2

#edit working dir for different task arrays on cluster (set your directory)
cd ~/outbreaksimulator/abc_output/${RUN_NAME}

# The job command(s):
time R --no-save --args $RUN_NAME < 01_init.R