#!/bin/env bash
#SBATCH --time=15:00:00
#SBATCH --job-name=LSDworkshop2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --output=LSDworkshop_2_%A_%a.out
#SBATCH --array=1


START=$(date "+%s")


module purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

. venv/bin/activate

python3 scenarios/LSD_workshop_2_detection_two_weeks.py $VER $SLURM_ARRAY_TASK_ID


END=$(date "+%s")
echo -e "\n"
TOTAL_SECONDS=$((END-START))
printf "ran in %02d:%02d:%02d\n" $((TOTAL_SECONDS/3600)) $((TOTAL_SECONDS%3600/60)) $((TOTAL_SECONDS%60))


