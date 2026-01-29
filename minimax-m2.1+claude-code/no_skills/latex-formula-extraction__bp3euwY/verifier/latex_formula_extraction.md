$$\mathcal{L}_{total} = \mathcal{L}_{CE} + \lambda \mathcal{L}_{KL}$$
$$y_i = \text{softmax}(x_i) = \frac{e^{x_i}}{\sum_{j=1}^{K} e^{x_j}}$$
$$\mathcal{L}_{CE} = - \sum_{i=1}^{C} y_i \log(\hat{y}_i)$$
$$p(z|x) = \mathcal{N}(z; \mu_{\phi}(x), \sigma^2_{\phi}(x))$$
$$\mathcal{L}_{KL} = - \frac{1}{2} \sum_{j=1}^{J} (1 + \log((\sigma_j)^2) - (\mu_j)^2 - (\sigma_j)^2)$$
$$p_\theta(z|x) = \mathcal{N}(z; \mu_\theta(x), \sigma^2_\theta(x))$$
$$q_\phi(z|x) = \mathcal{N}(z; \mu_\phi(x), \sigma^2_\phi(x))$$
$${\bf \delta} = \mu_{\theta}(x) - \mu_{\phi}(x)$$
$${\bf \Sigma} = \text{diag}(\sigma^2_{\theta}(x), \sigma^2_{\phi}(x))$$

$${\bf \delta} = \mathbf{\mu}_{\theta}(x) - \mathbf{\mu}_{\phi}(x)$$
$${\bf \Sigma} = \mathbf{\text{diag}}(\sigma^2_{\theta}(x), \sigma^2_{\phi}(x))$$
