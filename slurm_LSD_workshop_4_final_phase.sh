#!/bin/env bash
#SBATCH --time=30:00:00
#SBATCH --job-name=LSDworkshop4
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --output=LSDworkshop_4_%A_%a.out
#SBATCH --array=1


START=$(date "+%s")


module purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

. venv/bin/activate

python3 scenarios/LSD_workshop_4_final_phase.py $UNDETECTEDVER $DETECTIONVER $TWOWEEKSVER $TWOWEEKSRESOURCING $SLURM_ARRAY_TASK_ID $RESOURCING $VACCINATION

python3 scenarios/LSD_workshop_8_plotting_workshop_part3.py $UNDETECTEDVER $DETECTIONVER $TWOWEEKSVER $TWOWEEKSRESOURCING $SLURM_ARRAY_TASK_ID $RESOURCING $VACCINATION

python3 scenarios/LSD_workshop_10_plot_column_figures.py scenarios/LSD_workshop/${UNDETECTEDVER}_${DETECTIONVER}_${TWOWEEKSVER}_${TWOWEEKSRESOURCING}_06_final_${SLURM_ARRAY_TASK_ID}_${RESOURCING}_${VACCINATION}/properties_${UNDETECTEDVER}_${DETECTIONVER}_${TWOWEEKSVER}_${TWOWEEKSRESOURCING}_06_final_${SLURM_ARRAY_TASK_ID}_${RESOURCING}_${VACCINATION}



END=$(date "+%s")
echo -e "\n"
TOTAL_SECONDS=$((END-START))
printf "ran in %02d:%02d:%02d\n" $((TOTAL_SECONDS/3600)) $((TOTAL_SECONDS%3600/60)) $((TOTAL_SECONDS%60))


