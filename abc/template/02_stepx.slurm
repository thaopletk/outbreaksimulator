#!/bin/bash

#SBATCH --partition="sapphire"
#SBATCH --array=101-150
#SBATCH --mem=16G
#SBATCH --parsable
##SBATCH -o batch-output.log
##SBATCH --open-mode=append
#SBATCH --mail-type=END      # Type of email notification- BEGIN,END,FAIL,ALL
#SBATCH --mail-type=FAIL      # Type of email notification- BEGIN,END,FAIL,ALL
#SBATCH --mail-user=sllee2@student.unimelb.edu.au

#module load GCC/11.3.0
#module load OpenMPI/4.1.4
#module load r/3.6.2
module load foss/2022a R/4.2.2

#edit working dir for different task arrays on cluster (set your directory)
cd ~/outbreaksimulator/abc_output/${RUN_NAME}

echo "Slurm job id $SLURM_ARRAY_JOB_ID reporting in from `hostname`: task number = $SLURM_ARRAY_TASK_ID"

# The job command(s):
time R --no-save --args --parallel --type=MPI --cpus=$SLURM_NTASKS-1 < 02_stepx.R
