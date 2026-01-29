$$f \in L^1_{loc}([0,\infty);L^2(\mathbb{R}^n))$$
$$u_0 \in L^2_\sigma(\mathbb{R}^n)$$
$$\partial_t u + (u \cdot \nabla) u = - \nabla p + \Delta u + f, \quad x \in \mathbb{R}^n, t > 0$$
$$\nabla \cdot u = 0, \quad x \in \mathbb{R}^n, t > 0$$
$$u(x,0) = u_0(x), \quad x \in \mathbb{R}^n$$
$$p(x,t) = \sum_{j=1}^n \partial_j \int_{\mathbb{R}^n} \partial_j G(x-y) \cdot (u \otimes u)(y,t) \, dy$$
$$u(x,t) = e^{t\Delta} u_0(x) + \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \, ds + \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) \, ds$$
$$\mathbb{P} = I - \nabla \Delta^{-1} \nabla \cdot$$
$$\nabla \cdot e^{t\Delta} u_0 = 0$$
$$\nabla \cdot \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \, ds = 0$$
$$\nabla \cdot \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) \, ds = 0$$
$$\|e^{t\Delta} u_0\|_{L^2} \leq \|u_0\|_{L^2}$$
$$\|e^{t\Delta} u_0\|_{\dot{H}^s} \leq C t^{-s/2} \|u_0\|_{L^2}$$
$$\|e^{t\Delta} u_0\|_{L^{2^*}} \leq C t^{-n/4} \|u_0\|_{L^2}$$
$$\| \nabla e^{t\Delta} u_0 \|_{L^{2^*}} \leq C t^{-1/2} \|u_0\|_{L^2}$$
$$\| e^{t\Delta} u_0 \|_{L^{p}} \leq C t^{-\frac{n}{2}(\frac{1}{2} - \frac{1}{p})} \|u_0\|_{L^2}$$
$$\| \nabla e^{t\Delta} u_0 \|_{L^{q}} \leq C t^{-\frac{1}{2} - \frac{n}{2}(\frac{1}{2} - \frac{1}{q})} \|u_0\|_{L^2}$$
$$\| e^{t\Delta} \mathbb{P} f \|_{L^r} \leq C t^{-\frac{n}{2}(\frac{1}{p} - \frac{1}{r})} \|f\|_{L^p}$$
$$\| \nabla e^{t\Delta} \mathbb{P} f \|_{L^r} \leq C t^{-\frac{1}{2} - \frac{n}{2}(\frac{1}{p} - \frac{1}{r})} \|f\|_{L^p}$$
$$ \| \mathbb{P} (u \cdot \nabla u) \|_{L^p} \leq C \| u \|_{L^{2p}} \| \nabla u \|_{L^{2p}} $$
$$ \| \mathbb{P} (u \cdot \nabla u) \|_{L^{p}} \leq C \| u \|_{L^{\frac{np}{n-p}}} \| \nabla u \|_{L^{p}} $$
$$\| (u \cdot \nabla) u \|_{L^{\frac{2p}{p+1}}} \leq C \| u \|_{L^{2p}} \| \nabla u \|_{L^{2p}}$$
$$\| (u \cdot \nabla) u \|_{L^{\frac{p}{p+1}}} \leq C \| u \|_{L^{\frac{np}{n-p}}} \| \nabla u \|_{L^{p}}$$
$$ \dot{X}_p = \{ v \in \mathcal{S}'(\mathbb{R}^n) : \sup_{t \in (0,T)} t^{\alpha} \| v(t) \|_{L^p} < \infty \} $$
$$ \dot{X}_{p,\infty} = \{ v \in \mathcal{S}'(\mathbb{R}^n) : \sup_{t \in (0,T)} t^{\alpha} \| v(t) \|_{L^p,\infty} < \infty \} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^p} \leq C \int_0^t (t-s)^{-\frac{n}{2}(\frac{1}{q} - \frac{1}{p})} \| (u \cdot \nabla) u(s) \|_{L^q} ds $$
$$ \int_0^t (t-s)^{-\gamma} s^{-\beta} ds \leq C t^{1-\gamma-\beta} $$
$$ \| u \|_{L^p} \leq C \|u_0\|_{L^2}^{\theta} \| u \|_{X_{p}}^{1-\theta} $$
$$ \| u \|_{L^p} \leq C \|u_0\|_{L^2}^{\theta} \| \nabla u \|_{X_{p}}^{1-\theta} $$
$$ \beta(p) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} \right) $$
$$ \gamma(p) = \frac{n}{2} \left( \frac{1}{q} - \frac{1}{p} \right) $$
$$ \beta(p) + \beta(q) = 1 - \gamma(p) $$
$$ \beta(p) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} \right), \quad \beta(q) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{q} \right) $$
$$ \frac{1}{p} + \frac{1}{q} = 1 $$
$$ \beta(p) + \beta(q) = \frac{n}{2} \left(1 - \left( \frac{1}{p} + \frac{1}{q} \right) \right) = \frac{n}{2} \left(1 - 1 \right) = 0 $$
$$ 0 < \beta(p) < 1, \quad 0 < \beta(q) < 1 $$
$$ \frac{1}{p} + \frac{1}{q} = \frac{3}{4} $$
$$ \beta(p) + \beta(q) = \frac{n}{2} \left( \frac{3}{4} - \frac{1}{p} - \frac{1}{q} \right) $$
$$ \frac{1}{p} + \frac{1}{q} = \frac{3}{4} $$
$$ \beta(p) + \beta(q) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} + \frac{1}{2} - \frac{1}{q} \right) = \frac{n}{2} \left( 1 - \frac{3}{4} \right) = \frac{n}{8} $$
$$ \frac{1}{p} + \frac{1}{q} = \frac{3}{4} $$
$$ \frac{1}{p} + \frac{1}{q} = \frac{5}{6} $$
$$ \beta(p) + \beta(q) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} + \frac{1}{2} - \frac{1}{q} \right) = \frac{n}{2} \left( 1 - \frac{5}{6} \right) = \frac{n}{12} $$
$$ \| \nabla u \|_{L^{\frac{2p}{p+1}}} \leq C \| u \|_{X_p}^{\theta} \| \nabla u \|_{X_p}^{1-\theta} \| u_0 \|_{L^2}^{1-\theta} $$
$$ \| (u \cdot \nabla) u \|_{L^{\frac{p}{p+1}}} \leq C T^{\frac{n}{12}} \| u \|_{X_p} \| \nabla u \|_{X_p} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^p} \leq C T^{\frac{n}{12}} \| u \|_{X_p} \| \nabla u \|_{X_p} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^p} \leq C T^{\alpha} \| f \|_{L^1(0,T;L^2)} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^p} \leq C \| f \|_{L^1(0,T;L^2)} \int_0^t (t-s)^{-\frac{n}{4}} ds \leq C T^{\frac{1}{2} - \frac{n}{4}} \| f \|_{L^1(0,T;L^2)} $$
$$ \alpha = \frac{1}{2} - \frac{n}{4} $$
$$ \alpha = \frac{1}{2} - \frac{n}{2p} $$
$$ \alpha = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} \right) $$
$$ u \in C([0,T]; L^2_\sigma) \cap L^2_{loc}(0,\infty; \dot{H}^1) $$
$$ \| u \|_{L^\infty(0,T; L^2)} + \| \nabla u \|_{L^2(0,T; L^2)} \leq C $$
$$ \| u \|_{L^p(t,t+T; L^p)} \leq C $$
$$ \mathcal{X} = \{ v \in L^\infty(0,T; L^2) \cap L^2(0,T; \dot{H}^1) : \nabla \cdot v = 0 \} $$
$$ \| u \|_{L^\infty(0,T; L^2)} \leq C, \quad \| \nabla u \|_{L^2(0,T; L^2)} \leq C $$
$$ \frac{d}{dt} \| u(t) \|_{L^2}^2 + 2 \| \nabla u(t) \|_{L^2}^2 = 2 \langle f(t), u(t) \rangle $$
$$ | \langle f(t), u(t) \rangle | \leq \| f(t) \|_{L^2} \| u(t) \|_{L^2} \leq \frac{1}{2} \| f(t) \|_{L^2}^2 + \frac{1}{2} \| u(t) \|_{L^2}^2 $$
$$ \| u(t) \|_{L^2}^2 \leq \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds + \int_0^t \| u(s) \|_{L^2}^2 ds $$
$$ \| u(t) \|_{L^2}^2 \leq \exp(t) \left( \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds \right) $$
$$ \frac{1}{2} \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 = \langle \nabla f(t), \nabla u(t) \rangle - \langle \nabla (u \cdot \nabla u), \nabla u \rangle $$
$$ \langle \nabla (u \cdot \nabla u), \nabla u \rangle = - \langle (u \cdot \nabla) u, \Delta u \rangle $$
$$ | \langle (u \cdot \nabla) u, \Delta u \rangle | \leq \| (u \cdot \nabla) u \|_{L^2} \| \Delta u \|_{L^2} $$
$$ \| (u \cdot \nabla) u \|_{L^2} \leq \| u \|_{L^4} \| \nabla u \|_{L^4} \leq C \| u \|_{H^1} \| \nabla u \|_{H^1} $$
$$ | \langle \nabla f(t), \nabla u(t) \rangle | \leq \| \nabla f(t) \|_{L^2} \| \nabla u(t) \|_{L^2} \leq \frac{1}{2} \| \nabla f(t) \|_{L^2}^2 + \frac{1}{2} \| \nabla u(t) \|_{L^2}^2 $$
$$ \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 \leq \| \nabla f(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 + C \| u \|_{H^1}^2 \| \nabla u \|_{H^1}^2 $$
$$ \| u \|_{L^p(t,t+T; L^p)} \leq C(T) $$
$$ \int_{t}^{t+T} \| u(s) \|_{L^p}^p ds \leq C(T) $$
$$ \| v \|_{L^2(0,T; H^1)} \leq C \| v \|_{L^\infty(0,T; L^2)} $$
$$ \| v \|_{L^2(0,T; H^2)} \leq C \| v \|_{L^2(0,T; L^2)}^{1/2} \| \Delta v \|_{L^2(0,T; L^2)}^{1/2} $$
$$ \| \Delta v \|_{L^2(0,T; L^2)} \leq \| \nabla v \|_{L^2(0,T; L^2)}^{1/2} \| \nabla^2 v \|_{L^2(0,T; L^2)}^{1/2} $$
$$ \| \nabla v \|_{L^\infty(0,T; L^2)} \leq C \| v \|_{L^\infty(0,T; L^2)} $$
$$ \nabla^2 v \in L^2(0,T; L^2) $$
$$ \| \nabla v \|_{L^2(0,T; L^2)} \leq C \| v \|_{L^\infty(0,T; L^2)} $$
$$ \| \Delta v \|_{L^2(0,T; L^2)} \leq C \| \Delta v \|_{L^2(0,T; L^2)} $$
$$ \| u \|_{L^2(0,T; H^2)} \leq C $$
$$ \| u \|_{L^p(t,t+T; L^p)} \leq C $$
$$ \frac{1}{2} \frac{d}{dt} \| u(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 = \langle f(t), u(t) \rangle $$
$$ \int_{t}^{t+T} \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2} \| u(s) \|_{L^2} ds $$
$$ \| u(t) \|_{L^2}^2 \leq C, \quad \int_{t}^{t+T} \| \nabla u(s) \|_{L^2}^2 ds \leq C $$
$$ \frac{1}{2} \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u(t-T) \|_{L^2}^2 + \int_{t-T}^{t} \| f(s) \|_{L^2} \| u(s) \|_{L^2} ds $$
$$ \sup_{t \in [0,T]} \| u(t) \|_{L^2}^2 \leq C \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
$$ \int_0^T \| \nabla u(s) \|_{L^2}^2 ds \leq C \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
$$ \int_t^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( 1 + \int_{t-T}^{t+T} \| f(s) \|_{L^2}^2 ds \right) $$
$$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \int_{t}^{t+T} \| u(s) \|_{L^4}^4 ds \right) $$
$$ \| u \|_{L^4(t,t+T; L^4)} \leq C(T) $$
$$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \int_{t}^{t+T} \| u(s) \|_{L^4}^4 ds \right) $$
$$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \| u \|_{L^4(t,t+T; L^4)}^4 \right) $$
$$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \| u \|_{L^4(t,t+T; L^4)}^4 \right) $$
$$ \| u \|_{L^2(0,T; H^2)} \leq C(T) $$
$$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C \| \nabla u \|_{L^2(0,T; H^1)}^{1/2} \| \nabla u \|_{L^2(0,T; H^2)}^{1/2} $$
$$ \| \nabla u \|_{L^2(0,T; H^1)} \leq C \| u \|_{L^2(0,T; H^2)} $$
$$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
$$ \int_{t}^{t+T} \| \nabla u(s) \|_{L^4}^4 ds \leq C(T) $$
$$ \int_{t}^{t+T} \| \nabla^2 u(s) \|_{L^2}^2 ds \leq C(T) $$
$$ \| \nabla u \|_{L^4(t,t+T; L^4)} \leq C(T) $$
$$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
$$ \| u \|_{L^\infty(0,T; L^2)} + \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
$$ \| u(t) \|_{L^p} \leq C(p,T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \| u \|_{L^\infty(0,T; L^\infty)} \leq C(T) $$
$$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ u \in C([0,T]; L^2_\sigma) $$
$$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
$$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
$$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
$$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
$$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
$$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ \frac{d}{dt} \| u(t) \|_{L^2}^2 + 2 \| \nabla u(t) \|_{L^2}^2 = 2 \langle f(t), u(t) \rangle $$
$$ | \langle f(t), u(t) \rangle | \leq \| f(t) \|_{L^2} \| u(t) \|_{L^2} \leq \frac{1}{2} \| f(t) \|_{L^2}^2 + \frac{1}{2} \| u(t) \|_{L^2}^2 $$
$$ \| u(t) \|_{L^2}^2 \leq \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds + \int_0^t \| u(s) \|_{L^2}^2 ds $$
$$ \| u(t) \|_{L^2}^2 \leq \exp(t) \left( \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds \right) $$
$$ \int_0^t \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u_0 \|_{L^2}^2 + \frac{1}{2} \int_0^t \| f(s) \|_{L^2}^2 ds + \frac{1}{2} \int_0^t \| u(s) \|_{L^2}^2 ds $$
$$ \int_0^T \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u_0 \|_{L^2}^2 + \frac{1}{2} \int_0^T \| f(s) \|_{L^2}^2 ds + \frac{1}{2} \int_0^T \| u(s) \|_{L^2}^2 ds $$
$$ \int_0^T \| u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
$$ \int_0^T \| \nabla u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
$$ \frac{1}{2} \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 = \langle \nabla f(t), \nabla u(t) \rangle - \langle \nabla (u \cdot \nabla u), \nabla u \rangle $$
$$ \langle \nabla (u \cdot \nabla u), \nabla u \rangle = - \langle (u \cdot \nabla) u, \Delta u \rangle $$
$$ | \langle (u \cdot \nabla) u, \Delta u \rangle | \leq \| (u \cdot \nabla) u \|_{L^2} \| \Delta u \|_{L^2} $$
$$ \| (u \cdot \nabla) u \|_{L^2} \leq \| u \|_{L^4} \| \nabla u \|_{L^4} \leq C \| u \|_{H^1} \| \nabla u \|_{H^1} $$
$$ \| u \|_{H^1} \leq C \| \nabla u \|_{L^2}, \quad \| \nabla u \|_{H^1} \leq C \| \Delta u \|_{L^2} $$
$$ \| (u \cdot \nabla) u \|_{L^2} \leq C \| \nabla u \|_{L^2} \| \Delta u \|_{L^2} $$
$$ | \langle (u \cdot \nabla) u, \Delta u \rangle | \leq C \| \nabla u \|_{L^2} \| \Delta u \|_{L^2}^2 $$
$$ | \langle \nabla f(t), \nabla u(t) \rangle | \leq \| \nabla f(t) \|_{L^2} \| \nabla u(t) \|_{L^2} \leq \frac{1}{2} \| \nabla f(t) \|_{L^2}^2 + \frac{1}{2} \| \nabla u(t) \|_{L^2}^2 $$
$$ \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 \leq \| \nabla f(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 + C \| \nabla u \|_{L^2}^2 \| \Delta u \|_{L^2}^2 $$
$$ \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 \leq \| \nabla f(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 + C \| \nabla u \|_{L^2}^2 \| \Delta u \|_{L^2}^2 $$
$$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| \nabla u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| \nabla f(s) \|_{L^2}^2 ds \right) $$
$$ \| u \|_{L^4(t,t+T; L^4)} \leq C(T) $$
$$ \| u \|_{L^2(0,T; H^2)} \leq C(T) $$
$$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
$$ \| \nabla u \|_{L^4(0,T; L^4)} \leq C(T) $$
$$ \| u \|_{L^\infty(0,T; L^2)} + \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
$$ \| u(t) \|_{L^p} \leq C(p,T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \| u \|_{L^\infty(0,T; L^\infty)} \leq C(T) $$
$$ \int_0^T \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ u \in C([0,T]; L^2_\sigma) $$
$$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
$$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
$$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
$$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
$$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
$$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ u \in C([0,T]; L^2_\sigma) $$
$$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
$$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
$$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
$$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
$$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
$$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ u \in C([0,T]; L^2_\sigma) $$
$$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
$$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
$$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
$$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
$$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
$$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
$$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
$$ u \in C([0,T]; L^2_\sigma) $$
$$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
$$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
$$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
$$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
$$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
$$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
$$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
$$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
