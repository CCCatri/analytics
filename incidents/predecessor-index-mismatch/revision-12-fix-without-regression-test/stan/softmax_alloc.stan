// softmax_alloc: per-opportunity conditional allocation over a ragged risk set (used by the passer sub-model; usually prior-only).
// eta_r = a_pos[pos] + m[pl] + s[ps] + X beta; P(chosen) = exp(eta) / sum over the set.
data {
  int<lower=0> N;
  int<lower=0> M;
  array[N] int<lower=1> start;
  array[N] int<lower=1> len;
  array[N] int<lower=1> chosen;
  int<lower=0> K;
  matrix[M, K] X;
  int<lower=1> P;                     // players (+1 padding at index 1)
  int<lower=1> G;                     // position groups (+1 padding)
  int<lower=1> J;                     // (player, season) pairs observed (+1 padding): the sparse season states
  array[J] int<lower=0, upper=J> j_prev;   // the player's previous observed pair (0 = none: stationary start)
  vector<lower=0>[J] j_dt;            // seasons since that previous pair
  array[J] int<lower=1, upper=J> j_order;  // evaluation order of the pairs: every pair after its j_prev (pairs are coded in encounter order, not season order)
  int<lower=1> T;                     // defence team-seasons (+1 padding)
  array[M] int<lower=1, upper=P> pl;
  array[M] int<lower=1, upper=G> pos;
  array[M] int<lower=1, upper=J> ps;
  array[M] int<lower=1, upper=T> df;
  real<lower=0> beta_sd;
  real<lower=0> group_sd_scale;
  real<lower=0> player_sd_scale;
  real<lower=0> season_sd_scale;
  real<lower=0> lambda_rate;
  real<lower=0> defense_sd_scale;
}
parameters {
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
  vector[M] eta = a_pos[pos] + m[pl] + s[ps];
  if (K > 0) eta += X * beta;
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
  for (i in 1:N) target += eta[chosen[i]] - log_sum_exp(segment(eta, start[i], len[i]));
}
