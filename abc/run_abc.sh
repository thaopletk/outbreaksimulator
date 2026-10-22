#!/bin/env bash
#SBATCH --job-name=make_abc_slurm_code
# The maximum running time of the job in days-hours:mins:sec
#SBATCH --time=0-00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --mem=25G
#SBATCH --open-mode=append
#SBATCH --mail-type=ALL #END,FAIL
#SBATCH --mail-user=simin.lee1@student.unimelb.edu.au

# use name of .yaml file as run name
filename=${1}
run_name="${filename%.yaml}"
echo "$run_name"

# check the no. cpu
N_CPU=$(awk '/n_cpus:/ {gsub(/ /, "", $2); print $2}' ~/outbreaksimulator/config/"$filename")

# change array number
SCRIPT_PATH=~/outbreaksimulator/abc/template/02_stepx.slurm
MAX_ARRAY=$((101 + N_CPU - 1))
sed -i "s/#SBATCH --array=101-[0-9]\+/#SBATCH --array=101-${MAX_ARRAY}/" "$SCRIPT_PATH"

# check the length of tolerance
N_GEN=$(awk '/n_generations:/ {gsub(/ /, "", $2); print $2}' ~/outbreaksimulator/config/"$filename")

# slurm script path
SCRIPT_PATH=~/outbreaksimulator/abc/${run_name}.slurm

# generate slurm script
cat <<EOF > $SCRIPT_PATH
#!/bin/bash

#SBATCH --job-name=abc_template
#SBATCH --partition="sapphire"
#SBATCH -o batch-output.log
#SBATCH --open-mode=append
#SBATCH --ntasks=1
# The maximum running time of the job in days-hours:mins:sec
#SBATCH --time=2-00:00:00

filename=\${filename}
run_name="\${filename%.yaml}"
echo "\$run_name"

# make directory if does not exist
mkdir -p ~/outbreaksimulator/abc_output/\${run_name}

# Copy input data to the nodes fast local disk 
cp -r ~/outbreaksimulator/config/\${filename} ~/outbreaksimulator/abc_output/\${run_name}/\${filename} # preserve .yaml in case modified in the future
cp -r ~/outbreaksimulator/abc/template/. ~/outbreaksimulator/abc_output/\${run_name}
cd ~/outbreaksimulator/abc_output/\${run_name}

a=\${run_name}

## this is the handler, it just takes realtime input so jobs know how to reference each other.
## It's job is to submit all the other jobs and then leave.

JOBID0=\$(sbatch --job-name=init.\$a --partition="sapphire" --time=0-00:10:00 --export=RUN_NAME=\$a 01_init.slurm)
EOF


# add stepx + collate combination
PREV_JOB_VAR="JOBID0"

# defind time arrays
stepx_times=("0-06:00:00" "0-08:00:00" "0-12:00:00" "0-18:00:00" "1-00:00:00" "1-00:00:00" "1-12:00:00" "2-00:00:00")

for ((i=1; i<=N_GEN; i++)); do
  STEP_JOBID="JOBID$((i * 2 - 1))"
  COLLATE_JOBID="JOBID$((i * 2))"
  STEP_NAME="s${i}.\$a"
  # set stepx times
  if (( i <= ${#stepx_times[@]} )); then
    stepx_time="${stepx_times[i-1]}"
  else
    stepx_time="2-00:00:00"
  fi
  # set collate time
  collate_time="0-02:30:00"

  cat <<EOF >> $SCRIPT_PATH

$STEP_JOBID=\$(sbatch --depend=afterok:\$$PREV_JOB_VAR --job-name=$STEP_NAME --partition="sapphire" --time=$stepx_time --export=RUN_NAME=\$a 02_stepx.slurm)
$COLLATE_JOBID=\$(sbatch --depend=afterany:\$$STEP_JOBID --job-name=collate.\$a --partition="sapphire" --time=$collate_time --export=RUN_NAME=\$a 03_collate.slurm)
EOF

  PREV_JOB_VAR="$COLLATE_JOBID"
done



# add last echo in the slurm file
total_jobs=$((N_GEN * 2))
jobid_lines="  \$JOBID0,"

for ((j=1; j<=total_jobs; j++)); do
  jobid_lines+="  \$JOBID$j,"

done

cat <<EOF >> $SCRIPT_PATH

echo "jobs
$jobid_lines
queued in sequence:"

squeue -u \$USER -o "%.8A %.4C %.10m %.20E"
EOF

# run the script
sbatch --export=ALL,filename=$filename $SCRIPT_PATH