#!/bin/bash

#SBATCH --array=101-150
#SBATCH --mem=16G
#SBATCH --parsable
##SBATCH -o batch-output.log
##SBATCH --open-mode=append
#SBATCH --mail-type=END,FAIL      # Type of email notification- BEGIN,END,FAIL,ALL
#SBATCH --mail-user=sllee2@student.unimelb.edu.au

module --force purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

# Activate virtual environment
cd ~/outbreaksimulator
source venv/bin/activate

# Set working directory
cd ~/outbreaksimulator/abc_output/${RUN_NAME}

echo "Slurm job id $SLURM_ARRAY_JOB_ID reporting in from `hostname`: task number = $SLURM_ARRAY_TASK_ID"

# The job command(s):
python 02_stepx.py