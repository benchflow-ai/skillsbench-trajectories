Formula Comparison Table

Metric | Value
--- | ---
Expected Count | 5
Actual Count | 193
Missing Count | 5
Extra Count | 193

Missing Formulas (in expected but not in actual)
1. $$\frac{d^2x_i}{dt^2} = -\omega_0^2 x_i + \frac{kq^2}{m} \sum_{\substack{j=1 \\ j\neq i}}^N \frac{1}{\left(x_i - x_j\right)^2} \cdot \text{sgn}\left(x_i - x_j\right)$$
2. $$\rho_c(\tau) = \rho_1(\tau)\rho_2(\tau + \delta T)$$
3. $$H_{i,M} = (\hbar/2)\Omega^{(i)}\sigma_x^{(i)}\prod_{m=1}^{M} \exp\left[i\eta_{i,m}\left[a_m + a_m^\dagger\right)\right]$$
4. $$P_e(t) = \frac{1}{2N} \left[ 1 - \sum_{n=0}^{\infty} \sum_{i=0}^{N} P_n \cos \left( \Omega_n^{(i)} t \right) \right]$$
5. $$H_{i,M} = (\hbar/2)\Omega^{(i)}\sigma_x^{(i)}\prod_{m=1}^{M} \exp\left[i\eta_{i,m}\left(a_m + a_m^\dagger\right)\right]$$

Extra Formulas (in actual but not in expected)
1. $$f \in L^1_{loc}([0,\infty);L^2(\mathbb{R}^n))$$
2. $$u_0 \in L^2_\sigma(\mathbb{R}^n)$$
3. $$\partial_t u + (u \cdot \nabla) u = - \nabla p + \Delta u + f, \quad x \in \mathbb{R}^n, t > 0$$
4. $$\nabla \cdot u = 0, \quad x \in \mathbb{R}^n, t > 0$$
5. $$u(x,0) = u_0(x), \quad x \in \mathbb{R}^n$$
6. $$p(x,t) = \sum_{j=1}^n \partial_j \int_{\mathbb{R}^n} \partial_j G(x-y) \cdot (u \otimes u)(y,t) \, dy$$
7. $$u(x,t) = e^{t\Delta} u_0(x) + \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \, ds + \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) \, ds$$
8. $$\mathbb{P} = I - \nabla \Delta^{-1} \nabla \cdot$$
9. $$\nabla \cdot e^{t\Delta} u_0 = 0$$
10. $$\nabla \cdot \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \, ds = 0$$
11. $$\nabla \cdot \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) \, ds = 0$$
12. $$\|e^{t\Delta} u_0\|_{L^2} \leq \|u_0\|_{L^2}$$
13. $$\|e^{t\Delta} u_0\|_{\dot{H}^s} \leq C t^{-s/2} \|u_0\|_{L^2}$$
14. $$\|e^{t\Delta} u_0\|_{L^{2^*}} \leq C t^{-n/4} \|u_0\|_{L^2}$$
15. $$\| \nabla e^{t\Delta} u_0 \|_{L^{2^*}} \leq C t^{-1/2} \|u_0\|_{L^2}$$
16. $$\| e^{t\Delta} u_0 \|_{L^{p}} \leq C t^{-\frac{n}{2}(\frac{1}{2} - \frac{1}{p})} \|u_0\|_{L^2}$$
17. $$\| \nabla e^{t\Delta} u_0 \|_{L^{q}} \leq C t^{-\frac{1}{2} - \frac{n}{2}(\frac{1}{2} - \frac{1}{q})} \|u_0\|_{L^2}$$
18. $$\| e^{t\Delta} \mathbb{P} f \|_{L^r} \leq C t^{-\frac{n}{2}(\frac{1}{p} - \frac{1}{r})} \|f\|_{L^p}$$
19. $$\| \nabla e^{t\Delta} \mathbb{P} f \|_{L^r} \leq C t^{-\frac{1}{2} - \frac{n}{2}(\frac{1}{p} - \frac{1}{r})} \|f\|_{L^p}$$
20. $$ \| \mathbb{P} (u \cdot \nabla u) \|_{L^p} \leq C \| u \|_{L^{2p}} \| \nabla u \|_{L^{2p}} $$
21. $$ \| \mathbb{P} (u \cdot \nabla u) \|_{L^{p}} \leq C \| u \|_{L^{\frac{np}{n-p}}} \| \nabla u \|_{L^{p}} $$
22. $$\| (u \cdot \nabla) u \|_{L^{\frac{2p}{p+1}}} \leq C \| u \|_{L^{2p}} \| \nabla u \|_{L^{2p}}$$
23. $$\| (u \cdot \nabla) u \|_{L^{\frac{p}{p+1}}} \leq C \| u \|_{L^{\frac{np}{n-p}}} \| \nabla u \|_{L^{p}}$$
24. $$ \dot{X}_p = \{ v \in \mathcal{S}'(\mathbb{R}^n) : \sup_{t \in (0,T)} t^{\alpha} \| v(t) \|_{L^p} < \infty \} $$
25. $$ \dot{X}_{p,\infty} = \{ v \in \mathcal{S}'(\mathbb{R}^n) : \sup_{t \in (0,T)} t^{\alpha} \| v(t) \|_{L^p,\infty} < \infty \} $$
26. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^p} \leq C \int_0^t (t-s)^{-\frac{n}{2}(\frac{1}{q} - \frac{1}{p})} \| (u \cdot \nabla) u(s) \|_{L^q} ds $$
27. $$ \int_0^t (t-s)^{-\gamma} s^{-\beta} ds \leq C t^{1-\gamma-\beta} $$
28. $$ \| u \|_{L^p} \leq C \|u_0\|_{L^2}^{\theta} \| u \|_{X_{p}}^{1-\theta} $$
29. $$ \| u \|_{L^p} \leq C \|u_0\|_{L^2}^{\theta} \| \nabla u \|_{X_{p}}^{1-\theta} $$
30. $$ \beta(p) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} \right) $$
31. $$ \gamma(p) = \frac{n}{2} \left( \frac{1}{q} - \frac{1}{p} \right) $$
32. $$ \beta(p) + \beta(q) = 1 - \gamma(p) $$
33. $$ \beta(p) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} \right), \quad \beta(q) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{q} \right) $$
34. $$ \frac{1}{p} + \frac{1}{q} = 1 $$
35. $$ \beta(p) + \beta(q) = \frac{n}{2} \left(1 - \left( \frac{1}{p} + \frac{1}{q} \right) \right) = \frac{n}{2} \left(1 - 1 \right) = 0 $$
36. $$ 0 < \beta(p) < 1, \quad 0 < \beta(q) < 1 $$
37. $$ \frac{1}{p} + \frac{1}{q} = \frac{3}{4} $$
38. $$ \beta(p) + \beta(q) = \frac{n}{2} \left( \frac{3}{4} - \frac{1}{p} - \frac{1}{q} \right) $$
39. $$ \frac{1}{p} + \frac{1}{q} = \frac{3}{4} $$
40. $$ \beta(p) + \beta(q) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} + \frac{1}{2} - \frac{1}{q} \right) = \frac{n}{2} \left( 1 - \frac{3}{4} \right) = \frac{n}{8} $$
41. $$ \frac{1}{p} + \frac{1}{q} = \frac{3}{4} $$
42. $$ \frac{1}{p} + \frac{1}{q} = \frac{5}{6} $$
43. $$ \beta(p) + \beta(q) = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} + \frac{1}{2} - \frac{1}{q} \right) = \frac{n}{2} \left( 1 - \frac{5}{6} \right) = \frac{n}{12} $$
44. $$ \| \nabla u \|_{L^{\frac{2p}{p+1}}} \leq C \| u \|_{X_p}^{\theta} \| \nabla u \|_{X_p}^{1-\theta} \| u_0 \|_{L^2}^{1-\theta} $$
45. $$ \| (u \cdot \nabla) u \|_{L^{\frac{p}{p+1}}} \leq C T^{\frac{n}{12}} \| u \|_{X_p} \| \nabla u \|_{X_p} $$
46. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^p} \leq C T^{\frac{n}{12}} \| u \|_{X_p} \| \nabla u \|_{X_p} $$
47. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^p} \leq C T^{\alpha} \| f \|_{L^1(0,T;L^2)} $$
48. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^p} \leq C \| f \|_{L^1(0,T;L^2)} \int_0^t (t-s)^{-\frac{n}{4}} ds \leq C T^{\frac{1}{2} - \frac{n}{4}} \| f \|_{L^1(0,T;L^2)} $$
49. $$ \alpha = \frac{1}{2} - \frac{n}{4} $$
50. $$ \alpha = \frac{1}{2} - \frac{n}{2p} $$
51. $$ \alpha = \frac{n}{2} \left( \frac{1}{2} - \frac{1}{p} \right) $$
52. $$ u \in C([0,T]; L^2_\sigma) \cap L^2_{loc}(0,\infty; \dot{H}^1) $$
53. $$ \| u \|_{L^\infty(0,T; L^2)} + \| \nabla u \|_{L^2(0,T; L^2)} \leq C $$
54. $$ \| u \|_{L^p(t,t+T; L^p)} \leq C $$
55. $$ \mathcal{X} = \{ v \in L^\infty(0,T; L^2) \cap L^2(0,T; \dot{H}^1) : \nabla \cdot v = 0 \} $$
56. $$ \| u \|_{L^\infty(0,T; L^2)} \leq C, \quad \| \nabla u \|_{L^2(0,T; L^2)} \leq C $$
57. $$ \frac{d}{dt} \| u(t) \|_{L^2}^2 + 2 \| \nabla u(t) \|_{L^2}^2 = 2 \langle f(t), u(t) \rangle $$
58. $$ | \langle f(t), u(t) \rangle | \leq \| f(t) \|_{L^2} \| u(t) \|_{L^2} \leq \frac{1}{2} \| f(t) \|_{L^2}^2 + \frac{1}{2} \| u(t) \|_{L^2}^2 $$
59. $$ \| u(t) \|_{L^2}^2 \leq \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds + \int_0^t \| u(s) \|_{L^2}^2 ds $$
60. $$ \| u(t) \|_{L^2}^2 \leq \exp(t) \left( \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds \right) $$
61. $$ \frac{1}{2} \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 = \langle \nabla f(t), \nabla u(t) \rangle - \langle \nabla (u \cdot \nabla u), \nabla u \rangle $$
62. $$ \langle \nabla (u \cdot \nabla u), \nabla u \rangle = - \langle (u \cdot \nabla) u, \Delta u \rangle $$
63. $$ | \langle (u \cdot \nabla) u, \Delta u \rangle | \leq \| (u \cdot \nabla) u \|_{L^2} \| \Delta u \|_{L^2} $$
64. $$ \| (u \cdot \nabla) u \|_{L^2} \leq \| u \|_{L^4} \| \nabla u \|_{L^4} \leq C \| u \|_{H^1} \| \nabla u \|_{H^1} $$
65. $$ | \langle \nabla f(t), \nabla u(t) \rangle | \leq \| \nabla f(t) \|_{L^2} \| \nabla u(t) \|_{L^2} \leq \frac{1}{2} \| \nabla f(t) \|_{L^2}^2 + \frac{1}{2} \| \nabla u(t) \|_{L^2}^2 $$
66. $$ \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 \leq \| \nabla f(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 + C \| u \|_{H^1}^2 \| \nabla u \|_{H^1}^2 $$
67. $$ \| u \|_{L^p(t,t+T; L^p)} \leq C(T) $$
68. $$ \int_{t}^{t+T} \| u(s) \|_{L^p}^p ds \leq C(T) $$
69. $$ \| v \|_{L^2(0,T; H^1)} \leq C \| v \|_{L^\infty(0,T; L^2)} $$
70. $$ \| v \|_{L^2(0,T; H^2)} \leq C \| v \|_{L^2(0,T; L^2)}^{1/2} \| \Delta v \|_{L^2(0,T; L^2)}^{1/2} $$
71. $$ \| \Delta v \|_{L^2(0,T; L^2)} \leq \| \nabla v \|_{L^2(0,T; L^2)}^{1/2} \| \nabla^2 v \|_{L^2(0,T; L^2)}^{1/2} $$
72. $$ \| \nabla v \|_{L^\infty(0,T; L^2)} \leq C \| v \|_{L^\infty(0,T; L^2)} $$
73. $$ \nabla^2 v \in L^2(0,T; L^2) $$
74. $$ \| \nabla v \|_{L^2(0,T; L^2)} \leq C \| v \|_{L^\infty(0,T; L^2)} $$
75. $$ \| \Delta v \|_{L^2(0,T; L^2)} \leq C \| \Delta v \|_{L^2(0,T; L^2)} $$
76. $$ \| u \|_{L^2(0,T; H^2)} \leq C $$
77. $$ \| u \|_{L^p(t,t+T; L^p)} \leq C $$
78. $$ \frac{1}{2} \frac{d}{dt} \| u(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 = \langle f(t), u(t) \rangle $$
79. $$ \int_{t}^{t+T} \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2} \| u(s) \|_{L^2} ds $$
80. $$ \| u(t) \|_{L^2}^2 \leq C, \quad \int_{t}^{t+T} \| \nabla u(s) \|_{L^2}^2 ds \leq C $$
81. $$ \frac{1}{2} \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u(t-T) \|_{L^2}^2 + \int_{t-T}^{t} \| f(s) \|_{L^2} \| u(s) \|_{L^2} ds $$
82. $$ \sup_{t \in [0,T]} \| u(t) \|_{L^2}^2 \leq C \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
83. $$ \int_0^T \| \nabla u(s) \|_{L^2}^2 ds \leq C \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
84. $$ \int_t^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( 1 + \int_{t-T}^{t+T} \| f(s) \|_{L^2}^2 ds \right) $$
85. $$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \int_{t}^{t+T} \| u(s) \|_{L^4}^4 ds \right) $$
86. $$ \| u \|_{L^4(t,t+T; L^4)} \leq C(T) $$
87. $$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \int_{t}^{t+T} \| u(s) \|_{L^4}^4 ds \right) $$
88. $$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \| u \|_{L^4(t,t+T; L^4)}^4 \right) $$
89. $$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| f(s) \|_{L^2}^2 ds + \| u \|_{L^4(t,t+T; L^4)}^4 \right) $$
90. $$ \| u \|_{L^2(0,T; H^2)} \leq C(T) $$
91. $$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C \| \nabla u \|_{L^2(0,T; H^1)}^{1/2} \| \nabla u \|_{L^2(0,T; H^2)}^{1/2} $$
92. $$ \| \nabla u \|_{L^2(0,T; H^1)} \leq C \| u \|_{L^2(0,T; H^2)} $$
93. $$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
94. $$ \int_{t}^{t+T} \| \nabla u(s) \|_{L^4}^4 ds \leq C(T) $$
95. $$ \int_{t}^{t+T} \| \nabla^2 u(s) \|_{L^2}^2 ds \leq C(T) $$
96. $$ \| \nabla u \|_{L^4(t,t+T; L^4)} \leq C(T) $$
97. $$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
98. $$ \| u \|_{L^\infty(0,T; L^2)} + \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
99. $$ \| u(t) \|_{L^p} \leq C(p,T) $$
100. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
101. $$ \| u \|_{L^\infty(0,T; L^\infty)} \leq C(T) $$
102. $$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
103. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
104. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
105. $$ u \in C([0,T]; L^2_\sigma) $$
106. $$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
107. $$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
108. $$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
109. $$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
110. $$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
111. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
112. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
113. $$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
114. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
115. $$ \frac{d}{dt} \| u(t) \|_{L^2}^2 + 2 \| \nabla u(t) \|_{L^2}^2 = 2 \langle f(t), u(t) \rangle $$
116. $$ | \langle f(t), u(t) \rangle | \leq \| f(t) \|_{L^2} \| u(t) \|_{L^2} \leq \frac{1}{2} \| f(t) \|_{L^2}^2 + \frac{1}{2} \| u(t) \|_{L^2}^2 $$
117. $$ \| u(t) \|_{L^2}^2 \leq \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds + \int_0^t \| u(s) \|_{L^2}^2 ds $$
118. $$ \| u(t) \|_{L^2}^2 \leq \exp(t) \left( \| u_0 \|_{L^2}^2 + \int_0^t \| f(s) \|_{L^2}^2 ds \right) $$
119. $$ \int_0^t \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u_0 \|_{L^2}^2 + \frac{1}{2} \int_0^t \| f(s) \|_{L^2}^2 ds + \frac{1}{2} \int_0^t \| u(s) \|_{L^2}^2 ds $$
120. $$ \int_0^T \| \nabla u(s) \|_{L^2}^2 ds \leq \frac{1}{2} \| u_0 \|_{L^2}^2 + \frac{1}{2} \int_0^T \| f(s) \|_{L^2}^2 ds + \frac{1}{2} \int_0^T \| u(s) \|_{L^2}^2 ds $$
121. $$ \int_0^T \| u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
122. $$ \int_0^T \| \nabla u(s) \|_{L^2}^2 ds \leq C(T) \left( \| u_0 \|_{L^2}^2 + \| f \|_{L^1(0,T; L^2)}^2 \right) $$
123. $$ \frac{1}{2} \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 = \langle \nabla f(t), \nabla u(t) \rangle - \langle \nabla (u \cdot \nabla u), \nabla u \rangle $$
124. $$ \langle \nabla (u \cdot \nabla u), \nabla u \rangle = - \langle (u \cdot \nabla) u, \Delta u \rangle $$
125. $$ | \langle (u \cdot \nabla) u, \Delta u \rangle | \leq \| (u \cdot \nabla) u \|_{L^2} \| \Delta u \|_{L^2} $$
126. $$ \| (u \cdot \nabla) u \|_{L^2} \leq \| u \|_{L^4} \| \nabla u \|_{L^4} \leq C \| u \|_{H^1} \| \nabla u \|_{H^1} $$
127. $$ \| u \|_{H^1} \leq C \| \nabla u \|_{L^2}, \quad \| \nabla u \|_{H^1} \leq C \| \Delta u \|_{L^2} $$
128. $$ \| (u \cdot \nabla) u \|_{L^2} \leq C \| \nabla u \|_{L^2} \| \Delta u \|_{L^2} $$
129. $$ | \langle (u \cdot \nabla) u, \Delta u \rangle | \leq C \| \nabla u \|_{L^2} \| \Delta u \|_{L^2}^2 $$
130. $$ | \langle \nabla f(t), \nabla u(t) \rangle | \leq \| \nabla f(t) \|_{L^2} \| \nabla u(t) \|_{L^2} \leq \frac{1}{2} \| \nabla f(t) \|_{L^2}^2 + \frac{1}{2} \| \nabla u(t) \|_{L^2}^2 $$
131. $$ \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 + \| \Delta u(t) \|_{L^2}^2 \leq \| \nabla f(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 + C \| \nabla u \|_{L^2}^2 \| \Delta u \|_{L^2}^2 $$
132. $$ \frac{d}{dt} \| \nabla u(t) \|_{L^2}^2 \leq \| \nabla f(t) \|_{L^2}^2 + \| \nabla u(t) \|_{L^2}^2 + C \| \nabla u \|_{L^2}^2 \| \Delta u \|_{L^2}^2 $$
133. $$ \int_{t}^{t+T} \| \Delta u(s) \|_{L^2}^2 ds \leq C(T) \left( \| \nabla u(t) \|_{L^2}^2 + \int_{t}^{t+T} \| \nabla f(s) \|_{L^2}^2 ds \right) $$
134. $$ \| u \|_{L^4(t,t+T; L^4)} \leq C(T) $$
135. $$ \| u \|_{L^2(0,T; H^2)} \leq C(T) $$
136. $$ \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
137. $$ \| \nabla u \|_{L^4(0,T; L^4)} \leq C(T) $$
138. $$ \| u \|_{L^\infty(0,T; L^2)} + \| \nabla u \|_{L^\infty(0,T; L^2)} \leq C(T) $$
139. $$ \| u(t) \|_{L^p} \leq C(p,T) $$
140. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
141. $$ \| u \|_{L^\infty(0,T; L^\infty)} \leq C(T) $$
142. $$ \int_0^T \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
143. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
144. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
145. $$ u \in C([0,T]; L^2_\sigma) $$
146. $$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
147. $$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
148. $$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
149. $$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
150. $$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
151. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
152. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
153. $$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
154. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
155. $$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
156. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
157. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
158. $$ u \in C([0,T]; L^2_\sigma) $$
159. $$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
160. $$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
161. $$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
162. $$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
163. $$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
164. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
165. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
166. $$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
167. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
168. $$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
169. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
170. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
171. $$ u \in C([0,T]; L^2_\sigma) $$
172. $$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
173. $$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
174. $$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
175. $$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
176. $$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
177. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
178. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
179. $$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
180. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
181. $$ \int_{0}^{T} \| \nabla u(s) \|_{L^\infty}^2 ds \leq C(T) $$
182. $$ \| \nabla u(t) \|_{L^p} \leq C(p,T) $$
183. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
184. $$ u \in C([0,T]; L^2_\sigma) $$
185. $$ \| u(t) - u_0 \|_{L^2} \leq C T^\epsilon $$
186. $$ \| e^{t\Delta} u_0 - u_0 \|_{L^2} \leq C t^{1/2} \| \nabla u_0 \|_{L^2} $$
187. $$ \int_0^t \| e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) \|_{L^2} ds \leq C \int_0^t (t-s)^{-1/2} \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} ds $$
188. $$ \| u(s) \|_{L^4} \| \nabla u(s) \|_{L^4} \leq C \| u(s) \|_{H^2} \| \nabla u(s) \|_{H^1} \leq C $$
189. $$ \int_0^t (t-s)^{-1/2} ds \leq C t^{1/2} $$
190. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} (u \cdot \nabla u)(s) ds \|_{L^2} \leq C t^{1/2} $$
191. $$ \| \int_0^t e^{(t-s)\Delta} \mathbb{P} f(s) ds \|_{L^2} \leq C \int_0^t (t-s)^{-n/4} \| f(s) \|_{L^1} ds \leq C t^{1/2 - n/4} \| f \|_{L^1(0,T; L^1)} $$
192. $$ \| u(t) - e^{t\Delta} u_0 \|_{L^2} \leq C t^{1/2} $$
193. $$ \lim_{t \to 0} \| u(t) - u_0 \|_{L^2} = 0 $$
