# 상태공간 OMA와 SSBMD 상세 설명 노트

작성일: 2026-05-28  
대상: 연구자 본인, 향후 발표/강의/문서화용 정리본

---

## 1. 이 문서의 목적

이 문서는 다음 네 가지를 한 번에 정리하기 위한 것이다.

1. **전문가 수준 설명**: 상태공간 관점, state-space modal response, covariance, spectral density, lag, generalized eigenvalue problem이 어떻게 모드 분해로 이어지는지 이론적으로 정리한다.
2. **학부생 수준 설명**: 우화와 예시를 사용해 개념을 직관적으로 설명한다.
3. **전통적 고유치해석과의 연결**: `Kφ = (ω^2) Mφ`를 아는 독자가 데이터 기반 상태공간 OMA까지 자연스럽게 이어질 수 있도록 간극을 메운다.
4. **SSBMD의 의미 부각**: 상태변수 기반 spectral density와 covariance를 통해 heavy damping 구조의 모달 응답을 어떻게 분해하는지 정리한다.

---

## 2. 가장 짧은 핵심 요약

- **상태공간 관점**은 구조응답을 변위 하나의 크기로 보지 않고, **동적 상태 전체의 진화**로 보는 관점이다.
- **state-space modal response**는 각 모드의 응답을 단일 파형이 아니라 **상태벡터 안의 고유한 응답 방향과 궤적**으로 해석한 것이다.
- **covariance**는 시간영역에서의 동조성, **spectral density**는 진동수영역에서의 동조성이다.
- 단, spectral density는 단일 covariance matrix가 아니라 **lag를 포함한 covariance function**과 Fourier transform 관계를 가진다.
- 전통적 모드해석이 시스템 매트릭스를 고유분해해 모드를 찾는다면, 상태공간 OMA/SSBMD는 **응답이 만든 통계적 행렬**을 분해해 모드 방향을 복원한다.

---

## 3. 학부생 수준 직관 설명

## 3.1 그네 비유

운동장에 그네 여러 개가 있고 바람이 불어 동시에 흔들린다고 생각하자.

정지사진만 보면 지금 어디까지 갔는지만 보인다. 그러나 동영상을 보면 다음이 함께 보인다.

- 어느 그네는 왼쪽으로 많이 갔지만 거의 멈추려 한다.
- 어느 그네는 가운데에 있지만 속도가 가장 빠르다.
- 어느 그네는 오래 흔들리고, 어느 그네는 빨리 죽는다.

즉 **위치만 보면 불완전하고, 위치와 움직임을 같이 보면 그네의 성격이 보인다.**

이것이 상태공간 관점의 핵심이다.

- 위치만 보는 것: 지금 어디 있는가?
- 상태공간으로 보는 것: 지금 어디 있고, 얼마나 빠르게 움직이며, 다음에 어디로 가는가?

---

## 3.2 건물 진동으로 바꾸면

건물도 하나의 방식으로만 흔들리지 않는다. 1차, 2차, 3차 모드가 섞여 응답이 만들어진다.

약감쇠 구조에서는 주파수 그래프에서 피크가 비교적 선명하다. 하지만 오일댐퍼, TMD, 제진장치가 들어간 **중감쇠 또는 heavy damping 구조**에서는 피크가 퍼지고 겹친다. 그 상태에서는 단순 peak picking만으로는

- 이 피크가 몇 차 모드인지,
- 실제 감쇠비가 얼마인지,
- 서로 어떤 모드가 섞여 있는지

명확히 보기 어렵다.

그래서 상태공간 관점에서는 응답을 봉우리의 높이로만 보지 않고 **모드가 상태공간에서 만드는 방향과 궤적**으로 본다.

---

## 4. 상태공간 관점의 전문가 수준 설명

## 4.1 고전적 2차계에서 상태공간으로

고전적 다자유도 구조계는 보통

\[
M\ddot u + C\dot u + Ku = f
\]

로 쓴다. 이를 상태공간으로 바꾸면 예를 들어

\[
x(t)=\begin{bmatrix}u(t)\\ \dot u(t)\end{bmatrix},
\qquad
\dot x = Ax + Bf
\]

처럼 쓸 수 있다.

의미는 분명하다. 구조물의 현재 상태는 변위만으로 결정되지 않고 **변위와 속도(또는 변위와 가속도 등 선택된 상태변수의 조합)**를 함께 봐야 한다는 것이다.

이때 상태공간 관점은 다음 질문을 가능하게 한다.

> 이 구조는 현재 어느 위치에 있는가?가 아니라,
> 이 구조는 지금 어떤 동적 상태로 움직이고 있는가?

이 질문이 모드분해에 중요한 이유는, 모드가 단순한 크기 패턴이 아니라 **상태벡터 안의 고유한 방향**으로 나타나기 때문이다.

---

## 4.2 state-space modal response란 무엇인가

일반적인 modal response는 이 모드가 시간에 따라 얼마나 흔들리나라는 관점이다. 반면 state-space modal response는

> 각 모드의 응답을 상태벡터 안에서 분리해 표현한 것

이다.

즉 한 모드의 응답은 단순 스칼라 파형이 아니라,

- 변위 성분,
- 속도 또는 가속도 성분,
- 위상관계,
- 에너지 분포

를 함께 가진 상태응답으로 해석된다.

이 관점은 heavy damping 구조에서 특히 중요하다. 감쇠가 클수록 단순 amplitude peak는 흐려지고, 대신 **상태성분 간의 관계**가 모드를 더 잘 드러내기 때문이다.

---

## 5. covariance와 spectral density의 물리적 의미

## 5.1 covariance의 의미

상태벡터 `x(t)`의 covariance를 생각하자.

\[
R_{xx}(0)=E[x(t)x(t)^T]
\]

이것은 0-lag covariance matrix다. 직관적으로는

> 전체 시간 동안 상태변수들이 평균적으로 얼마나 같이 움직였는가?

를 모아 놓은 행렬이다.

예를 들어

- 양의 큰 값: 두 상태변수가 대체로 같은 방향으로 움직임
- 음의 큰 값: 대체로 반대 방향으로 움직임
- 0에 가까움: 동조성이 약함

즉 covariance는 **시간영역 평균 관점의 동조성**이다.

---

## 5.2 spectral density의 의미

상태벡터의 spectral density matrix는

\[
S_{xx}(\omega)=E[X(\omega)X(\omega)^*]
\]

로 쓴다. 여기서 `X(ω)`는 상태벡터의 Fourier transform이다.

이 행렬은 다음 의미를 가진다.

> 진동수 `ω`에서 상태변수들이 얼마나 같이 에너지를 가지고 움직이는가?

즉 covariance가 전체 평균적 관계라면 spectral density는 **주파수별 동조성**이다.

- 어떤 주파수에서는 1차 모드 성분이 지배적일 수 있고,
- 다른 주파수에서는 2차 모드 성분이 강할 수 있다.

spectral density는 바로 그 **주파수별 에너지 구조와 상관 구조**를 보여준다.

---

## 5.3 covariance와 spectral density의 관계

여기서 중요한 것은 단일 covariance matrix와 spectral density를 혼동하지 않는 것이다.

정확한 관계는 lag를 포함한 covariance function을 통해 주어진다.

\[
R_{xx}(\tau)=E[x(t)x(t+\tau)^T]
\]

그리고

\[
S_{xx}(\omega)=\int_{-\infty}^{\infty} R_{xx}(\tau)e^{-i\omega\tau}d\tau
\]

즉,

> **spectral density는 covariance function의 Fourier transform**이다.

반대로

\[
R_{xx}(\tau)=\frac{1}{2\pi}\int_{-\infty}^{\infty} S_{xx}(\omega)e^{i\omega\tau}d\omega
\]

이므로 둘은 Fourier pair이다.

따라서 0-lag covariance는

\[
R_{xx}(0)=\frac{1}{2\pi}\int_{-\infty}^{\infty} S_{xx}(\omega)d\omega
\]

즉 spectral density를 주파수 전체에 대해 적분한 값이다.

### 중요한 결론

- **0-lag covariance 하나로 spectral density를 구할 수는 없다.**
- spectral density를 얻으려면 **lag를 포함한 covariance function `R(τ)` 전체**가 필요하다.
- 0-lag covariance는 전체 에너지 총량이고,
- spectral density는 그 에너지가 주파수별로 어떻게 분포하는가를 보여준다.

---

## 6. lag가 왜 필요한가

학부생도 이해할 수 있게 말하면 이렇다.

같이 공부하는 두 학생을 생각하자.

- 항상 동시에 반응하면 lag 0에서 동조성이 크다.
- 한 학생이 늘 2초 뒤에 따라오면 lag 0에서는 약해 보이지만, lag 2초에서는 강하게 보인다.

즉 **시간지연을 고려해야 진짜 관계가 드러날 수 있다.**

진동도 마찬가지다.

5 Hz 성분이 강한 응답은 covariance function이 lag에 따라 5 Hz 주기로 진동하고, 10 Hz 성분이 강하면 더 빠르게 진동한다. 즉 lag-dependent covariance 안에는 이미 진동수 정보가 숨어 있고, Fourier transform이 그것을 spectral density로 바꿔 준다.

따라서 lag가 필요한 이유는 다음과 같다.

1. **주파수 정보를 복원하려면 시간지연 구조가 필요하다.**
2. **0-lag covariance는 총량만 말해주고 분포는 말해주지 못한다.**
3. **모드가 다른 주파수에 나타난다는 사실 자체가 lag-dependent correlation에 반영된다.**

---

## 7. 이것이 어떻게 모드분해로 이어지는가

이제 가장 중요한 다리를 놓는다.

당신이 이미 알고 있는 고전적 모드해석은 시스템 행렬의 고유분해다.

\[
K\phi = \omega^2 M\phi
\]

여기서 `φ`는 모드벡터이고, 구조계는 이 모드벡터들의 조합으로 응답한다.

즉

\[
u(t)=\Phi q(t)
\]

라고 쓸 수 있다.

상태공간에서도 비슷하다.

\[
x(t)=\Psi r(t)
\]

- `Ψ`: 상태공간에서의 모드 방향
- `r(t)`: 각 모드의 modal response

그러면 covariance는

\[
R_{xx}=E[xx^T]=\Psi E[rr^T]\Psi^T
\]

spectral density는

\[
S_{xx}(\omega)=\Psi S_{rr}(\omega)\Psi^*
\]

형태를 가진다.

즉 중요한 점은 다음이다.

> **응답이 만든 covariance와 spectral density도 결국 같은 modal subspace 위에서 구성된다.**

따라서 시스템 매트릭스를 직접 몰라도, 응답에서 만든 행렬을 분해하면 그 안에서 모드 방향이 다시 나타난다.

---

## 8. generalized eigenvalue problem의 의미

SSBMD에서는 개념적으로 다음과 같은 문제를 푼다.

\[
P(\omega)v = \lambda Var\,v
\]

또는

\[
Var^{-1}P(\omega)v = \lambda v
\]

여기서

- `P(ω)`: 특정 주파수에서의 state spectral matrix
- `Var`: 전체 covariance matrix
- `v`: 찾고 싶은 state-space modal direction

이다.

이 식을 Rayleigh quotient로 보면

\[
\lambda = \frac{v^*P(\omega)v}{v^*Var\,v}
\]

가 된다. 이 값의 의미는

> 전체 에너지 대비, 주파수 `ω`에서 그 방향으로 얼마나 에너지가 집중되는가?

이다.

즉 generalized eigenvector `v`는

> **그 주파수에서 전체 배경 에너지에 비해 가장 두드러지게 나타나는 상태 방향**

을 뜻한다.

이것이 바로 각 주파수대에서 지배적인 모드를 꺼낸다는 말의 수학적 의미다.

---

## 9. 다른 OMA 및 모드분해 방법과의 유사성과 차이

## 9.1 고전적 고유치해석과 비교

### 유사성
- 둘 다 구조가 선호하는 고유한 진동 방향을 찾는다.
- 결국 모드벡터, 고유진동수, 모달 응답을 찾으려는 목적은 같다.

### 차이
- 고전적 해석: `M, C, K` 같은 시스템 매트릭스를 알고 시작한다.
- 상태공간 OMA/SSBMD: 시스템 매트릭스를 모르고 **응답 데이터가 만든 통계 행렬**에서 시작한다.

즉 전자는 모델 기반, 후자는 데이터 기반이다.

---

## 9.2 PCA/POD와 비교

### 유사성
- covariance를 분해해 지배적인 방향을 찾는다는 점이 비슷하다.

### 차이
- PCA/POD는 주로 **분산이 큰 방향**을 찾는다.
- 상태공간 OMA/SSBMD는 **특정 주파수에서 구조적으로 지배적인 모드 방향**을 찾는다.
- 따라서 PCA는 주파수 구분력이 약하고, OMA는 주파수 선택성이 강하다.

---

## 9.3 FDD와 비교

FDD는 주파수별 출력 spectral density matrix를 SVD하여 모드를 추정한다.

### 유사성
- 둘 다 주파수별 spectral matrix를 분해한다.
- resonance 부근에서 dominant singular vector/eigenvector가 모드형상과 대응한다.

### 차이
- FDD는 보통 출력 응답 자체의 spectral density를 본다.
- 상태공간 OMA/SSBMD는 **상태변수 기반 spectral density**를 써서 변위-속도/가속도 관계까지 포함한다.
- SSBMD는 covariance를 함께 사용하여 **전체 에너지 대비 특정 주파수 에너지의 상대적 지배성**을 본다.

즉 FDD가 이 주파수에서 가장 강한 출력 패턴을 찾는다면, SSBMD는 이 주파수에서 전체 상태 구조에 비해 가장 모드다운 상태 방향을 찾는 데 더 가깝다.

---

## 9.4 SSI와 비교

SSI는 출력 correlation 또는 Hankel matrix로 상태행렬 `A`를 식별한 뒤, 그 `A`를 고유분해해 모드를 찾는다.

### 유사성
- 둘 다 state-space 관점을 쓴다.
- 둘 다 응답 데이터만으로 모드를 구한다.
- 둘 다 통계량(상관, covariance, spectral information)을 이용한다.

### 차이
- SSI는 먼저 **상태행렬을 식별**한다.
- SSBMD는 상태행렬을 명시적으로 세우지 않고 **spectral density와 covariance의 구조에서 직접 모드 방향을 추출**한다.

즉 SSI가 식별 후 고유분해라면, SSBMD는 응답 행렬의 직접 분해에 가깝다.

---

## 10. 전문가용 핵심 정리

### 10.1 한 문장 요약

> 고전 모드해석이 시스템 연산자의 고유분해라면, 상태공간 OMA/SSBMD는 응답이 만든 통계 연산자의 generalized 고유분해를 통해 같은 modal subspace를 데이터로부터 복원하는 방법이다.

### 10.2 물리적 의미

- covariance: 전체 시간 평균 관점에서의 동조성과 에너지 구조
- spectral density: 주파수별 동조성과 에너지 구조
- generalized eigenvector: 특정 주파수에서 가장 지배적인 state-space modal direction

### 10.3 SSBMD의 강점

- heavy damping 구조에서 유리함
- mode overlap 상황에서 분리력 향상
- 단순 peak 기반 접근보다 감쇠 해석력 우수
- 상태성분 간 관계를 이용하므로 비고전감쇠 구조에 더 본질적인 해석 가능

---

## 11. 학부생용 최종 결론

쉽게 말하면 이렇다.

- 건물은 여러 모드가 섞여 흔들린다.
- 상태공간 관점은 그 흔들림을 지금 얼마나 흔들렸나 하나로 보지 않고, 어떤 상태로 움직이고 있나로 본다.
- covariance는 시간영역에서 같이 움직이는 정도,
- spectral density는 주파수영역에서 같이 움직이는 정도다.
- 이 정보를 잘 모으면 이 주파수에서는 어떤 모드가 제일 강한가를 뽑아낼 수 있다.
- 그래서 결국 응답만 가지고도 모드 분해가 가능해진다.

---

## 12. 연구자용 최종 결론

기술적으로, 상태변수의 covariance는 전체 주파수 영역에 걸친 평균 에너지 및 상관 구조를, 상태변수의 spectral density matrix는 각 주파수에서의 에너지 및 상관 구조를 나타낸다. 선형 구조계의 응답은 modal superposition으로 표현되므로, 이 두 행렬은 동일한 modal subspace 위에서 구성된다. 따라서 특정 주파수에서의 state spectral matrix를 전체 covariance에 대해 generalized eigenvalue problem으로 분해하면, 그 주파수에서 전체 배경 에너지 대비 가장 지배적인 state-space modal direction이 추출된다. 이것이 SSBMD가 시스템 매트릭스를 직접 모르고도 응답만으로 모드 분해에 도달하는 이론적 다리다.

