# ⚡ Short-Circuit-Calc: Industrial Power System Analyzer

Este software é uma ferramenta interativa desenvolvida em **Python** e **Streamlit** para o dimensionamento técnico de subestações industriais de até 1000kVA (ou superior), com foco em correntes de curto-circuito, bitolas de cabos e seletividade de proteções.

## 🚀 Funcionalidades

- **Cálculo de Curto-Circuito ($I_{cc}$):** Estimativa da corrente simétrica no QGBT e atenuação nos CCMs por impedância de cabos.
- **Dimensionamento de Condutores:** Seleção automática de bitolas baseada na **NBR 5410** (Capacidade de condução).
- **Análise de Queda de Tensão:** Verificação de conformidade em regime nominal (Limite de 4%).
- **Seletividade de Proteção:** Sugestão de disjuntores de caixa moldada (MCCB) e ajustes de disparo ($I_r$ e $I_m$).
- **Exportação de Relatório:** Geração de memorial de cálculo profissional em **PDF**.

## 📚 Embasamento Teórico

O software utiliza as seguintes formulações para os cálculos de engenharia:

### 1. Corrente de Curto-Circuito no Transformador
A corrente de curto-circuito simétrica no secundário (considerando barra infinita no primário) é:
$$I_{cc\_trafo} = \frac{S_{n}}{\sqrt{3} \times V_{s} \times Z_{pu}}$$
*Onde $S_n$ é a potência nominal (kVA), $V_s$ a tensão secundária e $Z_{pu}$ a impedância percentual do trafo.*

### 2. Contribuição de Motores
Motores em partida direta contribuem para o curto-circuito nos primeiros ciclos (reatância subtransitória):
$$I_{cc\_motores} \approx \sum (I_{nom\_motor} \times 4)$$

### 3. Queda de Tensão ($\Delta V$)
Calculada considerando a impedância complexa do condutor (Resistência + Reatância):
$$\Delta V = \sqrt{3} \times I \times (R \cdot \cos\phi + X \cdot \sin\phi) \times L$$
*Sendo $R$ a resistência ôhmica e $X$ a reatância indutiva conforme a bitola selecionada.*

## 🛠️ Como Executar o Projeto

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com
    ```
2.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Inicie a aplicação:**
    ```bash
    streamlit run app.py
    ```

## 📦 Requisitos
- `streamlit`
- `pandas`
- `numpy`
- `reportlab`

---
**Desenvolvido para facilitar o dia a dia do engenheiro eletricista e projetista industrial.**
