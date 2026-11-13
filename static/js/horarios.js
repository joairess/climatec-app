(function () {
  const copiar = document.getElementById("copiar-codigo");
  if (copiar) {
    copiar.addEventListener("click", async function () {
      const codigo = copiar.dataset.codigo || "";
      try {
        await navigator.clipboard.writeText(codigo);
        copiar.textContent = "Código copiado";
      } catch (erro) {
        const alvo = document.getElementById("codigo-acompanhamento");
        if (!alvo) return;
        const selecao = window.getSelection();
        const faixa = document.createRange();
        faixa.selectNodeContents(alvo);
        selecao.removeAllRanges();
        selecao.addRange(faixa);
      }
    });
  }

  const form = document.querySelector("[data-horarios]");
  if (!form) return;
  const campoData = form.querySelector("#id_data");
  const caixa = form.querySelector("[data-slots]");
  const mensagem = form.querySelector("[data-slots-msg]");
  if (!campoData || !caixa || !mensagem) return;

  campoData.addEventListener("change", carregar);

  async function carregar() {
    if (!campoData.value) {
      mensagem.textContent = "Escolha uma data para ver os horários livres.";
      caixa.replaceChildren();
      return;
    }
    mensagem.textContent = "Carregando horários…";
    const extra = form.dataset.horariosExtra || "";
    try {
      const resposta = await fetch(
        form.dataset.horarios + "?data=" + encodeURIComponent(campoData.value) + extra,
        { headers: { Accept: "application/json" } }
      );
      const dados = await resposta.json();
      mensagem.textContent = dados.mensagem || "";
      desenhar(dados.slots || []);
    } catch (erro) {
      mensagem.textContent = "Não foi possível carregar os horários. Use o botão Ver horários livres.";
    }
  }

  function desenhar(slots) {
    caixa.replaceChildren();
    if (!slots.length) return;
    const grupo = document.createElement("div");
    grupo.className = "choice-cards";
    grupo.setAttribute("role", "radiogroup");
    grupo.setAttribute("aria-label", "Horários livres");
    slots.forEach(function (slot) {
      const rotulo = document.createElement("label");
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "horario";
      input.value = slot.value;
      input.required = true;
      const texto = document.createElement("span");
      texto.textContent = slot.label;
      rotulo.append(input, texto);
      grupo.append(rotulo);
    });
    caixa.append(grupo);
  }
})();
