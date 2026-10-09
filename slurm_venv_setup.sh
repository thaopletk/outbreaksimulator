#!/bin/env bash
#SBATCH --time=1:00:00
#SBATCH --job-name=venvsetup
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --output=venvsetup_%A_%a.out


START=$(date "+%s")


module purge
module load GCCcore/11.3.0
module load Python/3.10.4
module load texlive


python -m venv venv
. venv/bin/activate
python -m ensurepip --upgrade #if no pip
python -m pip install --upgrade pip
pip install -r slurm_requirements.txt
pip install numpy==2.2.6 scipy matplotlib libpysal contourpy
pip install openpyxl

END=$(date "+%s")
echo -e "\n"
TOTAL_SECONDS=$((END-START))
printf "ran in %02d:%02d:%02d\n" $((TOTAL_SECONDS/3600)) $((TOTAL_SECONDS%3600/60)) $((TOTAL_SECONDS%60))
