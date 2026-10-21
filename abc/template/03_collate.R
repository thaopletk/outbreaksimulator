"------- 3 Set-up --------"
#collate
setup.file = dget('Out/setup.file.txt')
setup.file
load(setup.file)

g<-dget('Out/g.txt') # get generation no. from `01_init.R`
g

# get estimates compiled from prev gen
if(g>1){load(paste0("Out/smc.abc.g",g-1,".postclust.RData")); g<-g+1} 
g

# prepare file names for current gen (to compile estimates later)
fns<-list.files(path = 'Out')
part_ids<-grep(paste0('^gen_',g,'_task_'),fns); # make sure it points to 'Out' folder
length(part_ids)

# check no of accepted particles across entire slurm array; if more than N.particles, remove the extras
if (length(part_ids) > N.particles){
  files_to_rm <- paste0('Out/',list.files(path="Out")[grep(paste0('^gen_',g,'_task_'),list.files(path="Out"))])[(N.particles+1):length(part_ids)]
  file.remove(files_to_rm)
  part_ids<-grep(paste0('^gen_',g,'_task_'),list.files(path = 'Out'))
}

# make N.particles whatever the number of accepted particles saved at this point
if(length(part_ids)< N.particles){N.particles<-length(part_ids)}
N.particles

if(g==1){ # gen 1
  
  # Empty matrices to store results
  theta.new<-matrix(ncol=length(paras.index),nrow=N.particles)
  
  # Empty vectors to store distances, iter no, seed
  dist.temporal.all <- dist.spatial.all <- iters.all <- seed.all <- matrix(nrow=N.particles,ncol=G)
  
  # Empty vectors to store weights
  w.old<-matrix(ncol=1,nrow=N.particles)
  w.new<-matrix(ncol=1,nrow=N.particles)
}

"------- 4 Compile ABC output from current generation --------"

theta.old<-theta.new # in `*.postclust.RData` if g>1

# create empty objects from which to compile particle values to
theta.store<-matrix(NA, nrow=N.particles, ncol=length(paras.index))
dist.temporal.store <-dist.spatial.store<-rep(NA,N.particles)
sim.temp.store<-matrix(NA, nrow=N.particles, ncol=length(t_start:t_end))
sim.t_e.store<-matrix(NA, nrow=N.particles, ncol=nrow(dat_today))
iters.store<-seed.store<-rep(NA,N.particles)

# compilation
for(tid.c in 1:N.particles){ # needs testing
  
  #preserve things that get written over
  dput(tid.c, "Out/c.tid.txt")
  dput(fns, "Out/c.fns.txt")
  dput(part_ids, "Out/c.part_ids.txt")
  load(paste0('Out/',fns[part_ids[tid.c]])) # loads the values/sim data of accepted particle
  #reinvigorate
  tid.c<-dget("Out/c.tid.txt")
  fns<-dget("Out/c.fns.txt")
  part_ids<-dget("Out/c.part_ids.txt")
  
  #collated outputs
  theta.store[tid.c,] <- as.numeric(paras[paras.index])
  dist.temporal.store[tid.c]<-distance.temporal
  dist.spatial.store[tid.c]<-distance.spatial
  sim.temp.store[tid.c,]<-sim.temporal$E
  sim.t_e.store[tid.c,]<-sim.t_e
  iters.store[tid.c]<-k
  seed.store[tid.c]<-seed
  
  cat(tid.c," of ",N.particles,
      " (",round(tid.c/N.particles*100,1),"%)","\n", sep=""); flush.console()
}

# make clean (!!! these are the OUTPUT)
theta.new<-theta.store # posteriors; gen-specific
dist.temporal.all[1:N.particles,g]<-dist.temporal.store # temporal distances; all gens
dist.spatial.all[1:N.particles,g]<-dist.spatial.store # temporal distances; all gens
sim.temp.all <- sim.temp.store # simulated curve (rows=particle, col=days); gen-specific 
sim.t_e.all <- sim.t_e.store # simulated t_e index (rows=particle, col=n_premises); gen-specific 
iters.all[1:N.particles,g]<-iters.store # index of accepted particle
seed.all[1:N.particles,g]<-seed.store # seed of accepted particle
rm(theta.store, dist.temporal.store, dist.spatial.store,
   sim.temp.store, sim.t_e.store, iters.store, k, seed.store)

"------- 5 Update weights --------"
if(g==1){w.new<-rep(1/N.particles,N.particles)} 

if(g>1){
  
  #dist.temp.scaled <- (dist.temporal.all[,g]-min(dist.temporal.all[,g],na.rm = T))/(max(dist.temporal.all[,g],na.rm = T)-min(dist.temporal.all[,g],na.rm = T))
  #dist.spat.scaled <- (dist.spatial.all[,g]-min(dist.spatial.all[,g],na.rm = T))/(max(dist.spatial.all[,g],na.rm = T)-min(dist.spatial.all[,g],na.rm = T))
  
  for(np in 1:N.particles){
      
    if (scenario == 10 || scenario == 20) {
        paras_dens<-list( beta_intra = NA, #within-farm beta transmission rate (S to E)
                          sigma_intra = NA, #within-farm 1/latent period transmission rate (E to I)
                          gamma_intra = NA, #within-farm 1/infectious duration transmission rate (I to R)
                          
                          alpha = NA, #background transmission rate
                          beta0 = NA, #baseline transmission rate
                          
                          kernel_type = NA, #1:exponential, 2:power_law, 3:cauchy, 4:cauchy_dist
                          psi = NA, #spatial kernel shape para
                          rho0 = NA, #spatial kernel shape para2 (estimated from MLE)
                          
                          zeta = NA, #the infectivity of all animals combined (i.e., for EI - single species)
                          zeta_1 = NA, #the infectivity of cattle to sheep
                          zeta_2 = NA, #the infectivity of pigs
                          zeta_3 = NA, #the infectivity of others
                          
                          chi = NA, # an index of the counts per species
                          
                          xi = NA,  #the susceptibility of all animals combined (i.e., for EI - single species)
                          xi_1 = NA, #the susceptibility of cattle from sheep
                          xi_2 = NA, #the susceptibility of pigs
                          xi_3 = NA, #the susceptibility of others
                          
                          theta = NA #vaccination effectiveness
                          
        )
    } else if (scenario == 30) {
        paras_dens<-list(beta_intra = NA, #within-farm beta transmission rate (S to E)
                         sigma_intra = NA, #within-farm 1/latent period transmission rate (E to I)
                         gamma_intra = NA, #within-farm 1/infectious duration transmission rate (I to R)
                         
                         alpha = NA, #background transmission rate
                         beta0 = NA, #baseline transmission rate
                         
                         kernel_type = NA, #1:exponential, 2:power_law, 3:cauchy, 4:cauchy_dist
                         psi = NA, #spatial kernel shape para
                         rho0 = NA, #spatial kernel shape para2 (estimated from MLE)
                         
                         zeta = NA, #the infectivity of all animals combined (i.e., for EI - single species)
                         zeta_1 = NA, #the infectivity of cattle to sheep
                         zeta_2 = NA, #the infectivity of pigs
                         zeta_3 = NA, #the infectivity of others
                         
                         chi = NA, # an index of the counts per species
                         
                         xi = NA,  #the susceptibility of all animals combined (i.e., for EI - single species)
                         xi_1 = NA, #the susceptibility of cattle from sheep
                         xi_2 = NA, #the susceptibility of pigs
                         xi_3 = NA, #the susceptibility of others
                         
                         theta = NA, #vaccination effectiveness
                         
                         add_c = NA, # recruitment of cattle
                         add_v = NA, # vector population recruitment
                         mu_c = NA, # natural death rate of cattle 
                         mu_v = NA, # natural death rate of vectors
                         
                         a1 = NA, # parameter for biting rate
                         a2 = NA, # parameter for biting rate
                         a3 = NA, # lower limit of temp
                         a4 = NA, # upper limit of temp
                         v_vc = NA, # probability of transmission from vector to cattle
                         v_cv = NA, # probability of transmission from cattle to vector
                         d_v = NA, # vector density
                         
                         omega = NA, # waning rate
                         mu_lsd = NA, # mortality rate of LSD
                         trans = NA, # virus survival rate on vectors
                         
                         scaling_c = NA, # scaling factor for transmission rate of cattle
                         scaling_v = NA # scaling factor for transmission rate of vector
        )
    }
    
    # prior probability of proposed param values
    
    paras_dens[paras.index.unif] <- sapply(1:length(paras.index.unif), function(x) 
      dunif(theta.new[np,x], min=lm.low[x], max=lm.upp[x])/(1/(lm.upp[x]-lm.low[x]))) #normalised by total density of each distribution,  so balanced across parameters, effectively gets this back to 1 if all uniform, allows for non-uniform in mix
    
    
    if (length(paras.index.ratio)>0) {
      paras_dens[paras.index.ratio] <- sapply(match(paras.index.ratio, paras.index), function(x) 
        dunif(log10(theta.new[np,x]), min=lm.low[x], max=lm.upp[x])/(1/(lm.upp[x]-lm.low[x])))
    }
    
    # weight numerator (w1)
    # for uniform prior, w1 should all be equal
    w1 <- prod(as.numeric(paras_dens[paras.index])) #* (1-dist.temp.scaled[np]) * (dist.spat.scaled[np])
      # (dist.temporal.all[np,g]) * (dist.spatial.all[np,g]) # undergoing some testing atm

    
    # weight denominator (w2), dnorm approach; weighted sum of likelihoods from the pertubation kernel
    w2 <- sapply(1:length(paras.index), function(a) 
      sum(w.old * dnorm((theta.new[np,a] - theta.old[,a])/ sqrt(2*tau.var.old[a]), mean=0, sd=1, log=F)))
    
    if (length(paras.index.ratio)>0) {
      w2[match(paras.index.ratio, paras.index)] <- sapply(match(paras.index.ratio, paras.index), function(a) 
        sum(w.old * dnorm((log10(theta.new[np,a]) - log10(theta.old[,a]))/ sqrt(2*tau.var.old[a]), mean=0, sd=1, log=F)))
    }
    
    w2 <- sum(w2)
    
    w.new[np] <- w1/w2 # *m/n - if more than one run per param set
    
    cat("weight calculations: ", np," of ",N.particles,
        " (",round(np/N.particles*100,1),"%)","\n", sep=""); flush.console()
  }
}


# Calculate empirical mean (theta.old) and variance (sigma/tau) for this generation - used in pertubation

theta.old <- theta.new
w.old<-w.new/sum(w.new,na.rm = T) #normalise weights to sum to 1
#sigma <- cov(theta.new[1:N.particles,]) 

tau.mu.old <- tau.var.old <- numeric()
for(i in 1:length(paras.index)){
  #weighted empirical mean of theta.old
  tau.mu.old[i]<- sum(theta.old[,i] * w.old)
  if (length(paras.index.ratio)>0) {
    if (i %in% match(paras.index.ratio, paras.index)) {
      tau.mu.old[i]<- sum(log10(theta.old[,i]) * w.old)
    }
  }
  
  #weighted empirical variance of theta.old
  tau.var.old[i] <- sum(w.old * (theta.old[,i] - tau.mu.old[i])^2) / ((N.particles - 1) / N.particles)
  if (length(paras.index.ratio)>0) {
    if (i %in% match(paras.index.ratio, paras.index)) {
      tau.var.old[i] <- sum(w.old * (log10(theta.old[,i]) - tau.mu.old[i])^2) / ((N.particles - 1) / N.particles)
    }
  }
}

# clear files
file.remove(paste0('Out/',list.files(path="Out")[grep("^c[.]",list.files(path="Out"))]))
(list.files(path="Out")[grep("^c[.]",list.files(path="Out"))])

rm(dat, dat_today, dat_ip, distmat) # dat_real

"------- 6 Save results --------"
save.image(paste0("Out/smc.abc.g",g,".postclust.RData"))

#increment step
g<-g+1
dput(g, 'Out/g.txt')

# restart seed counter
if (reproduce == TRUE){
  seed <- 1
  dput(seed, 'Out/seed.txt')
}
