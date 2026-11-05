// gain_t: discretised Student-t for integer non-scoring gains, restricted and renormalised to the legal support [lo, hi] of each play; weighted
// rows, reduce_sum over threads. q(y) = T_nu((y + 0.5 - mu)/sigma) - T_nu((y - 0.5 - mu)/sigma); P(y | L) = q(y) / sum_L q(v), through log CDFs.
// mu = alpha + X beta + a_pos[pos] + m[pl] + s[ps] + v_def[df]; log sigma = ls0 + ls_pos[pos]; nu = nu_min + nu_excess.
functions {
  real partial_lik(array[] int ys, int start, int end, vector w, vector mu, vector sig, array[] int lo, array[] int hi, real nu) {
    real lp = 0;
    for (i in start:end) {
      real up = student_t_lcdf((ys[i - start + 1] + 0.5 - mu[i]) / sig[i] | nu, 0, 1);
      real dn = student_t_lcdf((ys[i - start + 1] - 0.5 - mu[i]) / sig[i] | nu, 0, 1);
      real zu = student_t_lcdf((hi[i] + 0.5 - mu[i]) / sig[i] | nu, 0, 1);
      real zd = student_t_lcdf((lo[i] - 0.5 - mu[i]) / sig[i] | nu, 0, 1);
      lp += w[i] * (log_diff_exp(up, dn) - log_diff_exp(zu, zd));
    }
    return lp;
  }
}
data {
  int<lower=0> N;
  array[N] int y;
  vector<lower=0>[N] w;
  int<lower=1> grainsize;
  array[N] int lo;
  array[N] int hi;
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
  real<lower=0> log_sigma_sd;
  real<lower=0> nu_shape;
  real<lower=0> nu_rate;
  real<lower=0> nu_min;
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
  real ls0;
  vector[G] zls_pos;
  real<lower=0> sigma_ls;
  real<lower=0> nu_excess;
}
transformed parameters {
  vector[G] a_pos = sigma_pos * za_pos;
  vector[P] m = sigma_m * zm;
  vector[J] s;
  vector[T] v_def = sigma_def * zdef;
  vector[G] ls_pos = sigma_ls * zls_pos;
  real<lower=nu_min> nu = nu_min + nu_excess;
  a_pos[1] = 0;
  m[1] = 0;
  v_def[1] = 0;
  ls_pos[1] = 0;
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
  vector[N] mu = alpha + a_pos[pos] + m[pl] + s[ps] + v_def[df];
  vector[N] sig = exp(ls0 + ls_pos[pos]);
  if (K > 0) mu += X * beta;
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
  ls0 ~ normal(1, log_sigma_sd);
  zls_pos ~ std_normal();
  sigma_ls ~ normal(0, log_sigma_sd);
  nu_excess ~ gamma(nu_shape, nu_rate);
  if (N > 0) target += reduce_sum(partial_lik, y, grainsize, w, mu, sig, lo, hi, nu);
}
