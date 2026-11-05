// cat_hier: hierarchical multinomial logit over C categories (category 1 the reference), weighted rows, vectorised gathers.
// eta[, c] = alpha[c] + X beta[, c] + a_pos[pos, c] + m[pl, c] + s[ps, c] + m2[pl2, c] + v_def[df, c]
data {
  int<lower=0> N;
  int<lower=2> C;
  array[N] int<lower=1, upper=C> y;
  vector<lower=0>[N] w;
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
  array[N] int<lower=1, upper=P> pl2;
  real<lower=0> intercept_sd;
  real<lower=0> beta_sd;
  real<lower=0> group_sd_scale;
  real<lower=0> player_sd_scale;
  real<lower=0> season_sd_scale;
  real<lower=0> lambda_rate;
  real<lower=0> defense_sd_scale;
}
parameters {
  vector[C - 1] alpha;
  matrix[K, C - 1] beta;
  vector<lower=0>[C - 1] sigma_pos;
  vector<lower=0>[C - 1] sigma_m;
  vector<lower=0>[C - 1] sigma_m2;
  vector<lower=0>[C - 1] tau;
  real<lower=0> lambda;
  vector<lower=0>[C - 1] sigma_def;
  matrix[G, C - 1] za_pos;
  matrix[P, C - 1] zm;
  matrix[P, C - 1] zm2;
  matrix[J, C - 1] zs;
  matrix[T, C - 1] zdef;
}
transformed parameters {
  matrix[G, C - 1] a_pos;
  matrix[P, C - 1] m;
  matrix[P, C - 1] m2;
  matrix[J, C - 1] s;
  matrix[T, C - 1] v_def;
  for (c in 1:(C - 1)) {
    a_pos[, c] = sigma_pos[c] * za_pos[, c];
    m[, c] = sigma_m[c] * zm[, c];
    m2[, c] = sigma_m2[c] * zm2[, c];
    v_def[, c] = sigma_def[c] * zdef[, c];
    s[1, c] = 0;
    for (k in 2:J) {
      int j = j_order[k];
      if (j_prev[j] > 0) {
        real rho = exp(-lambda * j_dt[j]);
        s[j, c] = rho * s[j_prev[j], c] + tau[c] * sqrt(1 - rho * rho) * zs[j, c];
      } else s[j, c] = tau[c] * zs[j, c];
    }
  }
  a_pos[1, ] = rep_row_vector(0, C - 1);
  m[1, ] = rep_row_vector(0, C - 1);
  m2[1, ] = rep_row_vector(0, C - 1);
  v_def[1, ] = rep_row_vector(0, C - 1);
}
model {
  matrix[N, C] eta;
  eta[, 1] = rep_vector(0, N);
  for (c in 2:C) {
    int k = c - 1;
    eta[, c] = alpha[k] + a_pos[pos, k] + m[pl, k] + s[ps, k] + m2[pl2, k] + v_def[df, k];
    if (K > 0) eta[, c] += X * beta[, k];
  }
  alpha ~ normal(0, intercept_sd);
  to_vector(beta) ~ normal(0, beta_sd);
  sigma_pos ~ normal(0, group_sd_scale);
  sigma_m ~ normal(0, player_sd_scale);
  sigma_m2 ~ normal(0, player_sd_scale);
  tau ~ normal(0, season_sd_scale);
  lambda ~ exponential(lambda_rate);
  sigma_def ~ normal(0, defense_sd_scale);
  to_vector(za_pos) ~ std_normal();
  to_vector(zm) ~ std_normal();
  to_vector(zm2) ~ std_normal();
  to_vector(zs) ~ std_normal();
  to_vector(zdef) ~ std_normal();
  for (i in 1:N) target += w[i] * (eta[i, y[i]] - log_sum_exp(eta[i]));
}
