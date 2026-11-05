// betabinom_hier: hierarchical beta-binomial for a player's snaps on the field out of his side's snaps in one game.
// mu = inv_logit(alpha + X beta + a_pos[pos] + m[pl] + s[ps]); y ~ beta_binomial(n, mu phi, (1 - mu) phi). phi: the game-to-game spread of his rate.
data {
  int<lower=0> N;
  array[N] int<lower=0> y;
  array[N] int<lower=0> n;
  int<lower=0> K;
  matrix[N, K] X;
  int<lower=1> P;                     // players (+1 padding at index 1)
  int<lower=1> G;                     // position groups (+1 padding)
  int<lower=1> J;                     // (player, season) pairs observed (+1 padding): the sparse season states
  array[J] int<lower=0, upper=J> j_prev;   // the player's previous observed pair (0 = none: stationary start)
  vector<lower=0>[J] j_dt;            // seasons since that previous pair
  array[J] int<lower=1, upper=J> j_order;  // evaluation order of the pairs: every pair after its j_prev (pairs are coded in encounter order, not season order)
  int<lower=1> T;                     // defence team-seasons (+1 padding)
  array[N] int<lower=1, upper=P> pl;
  array[N] int<lower=1, upper=G> pos;
  array[N] int<lower=1, upper=J> ps;   // the row's (player, season) pair
  array[N] int<lower=1, upper=T> df;   // the row's defence team-season (1 = none)
  real<lower=0> intercept_sd;
  real<lower=0> beta_sd;
  real<lower=0> group_sd_scale;
  real<lower=0> player_sd_scale;
  real<lower=0> season_sd_scale;
  real<lower=0> lambda_rate;
  real<lower=0> defense_sd_scale;
  real log_phi_mean;
  real<lower=0> log_phi_sd;
}
parameters {
  real alpha;
  vector[K] beta;
  real<lower=0> sigma_pos;
  real<lower=0> sigma_m;
  real<lower=0> tau;
  real<lower=0> lambda;
  real<lower=0> sigma_def;
  vector[G] za_pos;
  vector[P] zm;
  vector[J] zs;
  vector[T] zdef;
  real<lower=0> phi;
}
transformed parameters {
  vector[G] a_pos = sigma_pos * za_pos;
  vector[P] m = sigma_m * zm;
  vector[J] s;
  vector[T] v_def = sigma_def * zdef;
  a_pos[1] = 0;
  m[1] = 0;
  v_def[1] = 0;
  s[1] = 0;
  for (k in 2:J) {
    int j = j_order[k];
    if (j_prev[j] > 0) {
      real rho = exp(-lambda * j_dt[j]);
      s[j] = rho * s[j_prev[j]] + tau * sqrt(1 - rho * rho) * zs[j];
    } else s[j] = tau * zs[j];
  }
}
model {
  vector[N] eta = alpha + a_pos[pos] + m[pl] + s[ps] + v_def[df];
  if (K > 0) eta += X * beta;
  alpha ~ normal(0, intercept_sd);
  beta ~ normal(0, beta_sd);
  sigma_pos ~ normal(0, group_sd_scale);
  sigma_m ~ normal(0, player_sd_scale);
  tau ~ normal(0, season_sd_scale);
  lambda ~ exponential(lambda_rate);
  sigma_def ~ normal(0, defense_sd_scale);
  za_pos ~ std_normal();
  zm ~ std_normal();
  zs ~ std_normal();
  zdef ~ std_normal();
  phi ~ lognormal(log_phi_mean, log_phi_sd);
  y ~ beta_binomial(n, inv_logit(eta) * phi, (1 - inv_logit(eta)) * phi);
}
