#!/bin/env bash
#SBATCH --time=15:00:00
#SBATCH --job-name=LSDworkshop3
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --output=LSDworkshop_3_%A_%a.out
#SBATCH --array=1


START=$(date "+%s")


module purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive

. venv/bin/activate

python3 scenarios/LSD_workshop_3_two_weeks_resourcing.py $UNDETECTEDVER $DETECTIONVER $SLURM_ARRAY_TASK_ID $RESOURCING

python3 scenarios/LSD_workshop_7_plotting_workshop_part2.py $UNDETECTEDVER $DETECTIONVER $SLURM_ARRAY_TASK_ID $RESOURCING

python3 scenarios/LSD_workshop_9_special_workshop_data_files.py $UNDETECTEDVER $DETECTIONVER $SLURM_ARRAY_TASK_ID $RESOURCING

python3 scenarios/LSD_workshop_10_plot_column_figures.py LSD_workshop/$UNDETECTEDVER_$DETECTIONVER_05_two_weeks_${SLURM_ARRAY_TASK_ID}_$RESOURCING/properties_$UNDETECTEDVER_$DETECTIONVER_05_two_weeks_${SLURM_ARRAY_TASK_ID}_$RESOURCING

END=$(date "+%s")
echo -e "\n"
TOTAL_SECONDS=$((END-START))
printf "ran in %02d:%02d:%02d\n" $((TOTAL_SECONDS/3600)) $((TOTAL_SECONDS%3600/60)) $((TOTAL_SECONDS%60))


