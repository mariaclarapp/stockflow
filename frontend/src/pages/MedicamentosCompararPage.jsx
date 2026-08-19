import { AlertCircle, ArrowLeft, ArrowRight, LoaderCircle, Pill, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { getMedicationComparison } from "../api/medications";
import { MedicationCategoryBadges } from "../components/medications/MedicationList";
import { stockQuantityText } from "../components/medications/medicationPresentation";

function parseIds(rawIds) {
  if (!rawIds) return { error: "Nenhum medicamento foi selecionado." };
  const parts = rawIds.split(",");
  if (parts.some((part) => !/^\d+$/.test(part) || Number(part) < 1)) {
    return { error: "A seleção informada na URL é inválida." };
  }
  const ids = [...new Set(parts.map(Number))];
  if (ids.length > 50) {
    return { error: "A comparação permite no máximo 50 medicamentos." };
  }
  return { ids };
}

function comparisonErrorMessage(error) {
  if (!(error instanceof ApiError) || error.status === 0) {
    return "Não foi possível carregar os medicamentos selecionados.";
  }
  if (error.status === 401 || error.status === 403) {
    return "Sua sessão não está disponível. Entre novamente.";
  }
  return error.message || "Não foi possível carregar os medicamentos selecionados.";
}

function MedicamentosCompararPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawIds = searchParams.get("ids");
  const parsed = useMemo(() => parseIds(rawIds), [rawIds]);
  const [medications, setMedications] = useState([]);
  const [competence, setCompetence] = useState(null);
  const [ups, setUps] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [missingIds, setMissingIds] = useState([]);

  useEffect(() => {
    let isCurrent = true;
    if (parsed.error) return undefined;

    async function loadMedications() {
      setIsLoading(true);
      setError("");
      try {
        const data = await getMedicationComparison(parsed.ids);
        if (!isCurrent) return;
        const returnedIds = new Set(data.medicamentos.map((item) => item.id));
        setMedications(data.medicamentos);
        setCompetence(data.competencia);
        setUps(data.ups);
        setMissingIds(parsed.ids.filter((id) => !returnedIds.has(id)));
        if (!data.medicamentos.length) {
          setError("Nenhum dos medicamentos informados foi encontrado.");
        }
      } catch (requestError) {
        if (isCurrent) {
          setMedications([]);
          setCompetence(null);
          setUps([]);
          setMissingIds([]);
          setError(comparisonErrorMessage(requestError));
        }
      } finally {
        if (isCurrent) setIsLoading(false);
      }
    }

    loadMedications();
    return () => {
      isCurrent = false;
    };
  }, [parsed.error, parsed.ids]);

  const displayedError = parsed.error || error;

  function removeMedication(id) {
    const nextIds = parsed.ids.filter((item) => item !== id);
    if (!nextIds.length) {
      navigate("/admin/medicamentos");
      return;
    }
    setSearchParams({ ids: nextIds.join(",") }, { replace: true });
  }

  return (
    <main className="medications-page medication-comparison-page">
      <Link className="detail-back-link" to="/admin/medicamentos">
        <ArrowLeft size={16} />
        Voltar para medicamentos
      </Link>

      <header className="page-heading medication-comparison-page__heading">
        <div>
          <span className="eyebrow">Visualização conjunta</span>
          <h1>Medicamentos selecionados</h1>
          <p>Compare os dados cadastrais e o estoque por UPS de até 50 apresentações.</p>
          {competence && (
            <small className="comparison-competence">
              Competência {String(competence.mes).padStart(2, "0")}/{competence.ano}
            </small>
          )}
        </div>
        {medications.length > 0 && (
          <button
            className="secondary-button"
            type="button"
            onClick={() => navigate("/admin/medicamentos")}
          >
            <Trash2 size={15} />
            Limpar todos
          </button>
        )}
      </header>

      {isLoading ? (
        <section className="comparison-page-state" aria-live="polite">
          <LoaderCircle className="button-spinner" size={26} />
          <strong>Carregando comparação...</strong>
        </section>
      ) : displayedError ? (
        <section className="comparison-page-state comparison-page-state--error" role="alert">
          <AlertCircle size={25} />
          <div>
            <strong>Não foi possível exibir a comparação</strong>
            <p>{displayedError}</p>
            <Link className="secondary-button" to="/admin/medicamentos">
              Voltar para medicamentos
            </Link>
          </div>
        </section>
      ) : (
        <>
          {missingIds.length > 0 && (
            <p className="comparison-warning" role="status">
              <AlertCircle size={16} />
              {missingIds.length === 1
                ? "Um medicamento da URL não foi encontrado e não será exibido."
                : `${missingIds.length} medicamentos da URL não foram encontrados e não serão exibidos.`}
            </p>
          )}
          <section className="medication-comparison-grid" aria-label="Medicamentos em comparação">
            {medications.map((medication) => (
              <article className="medication-comparison-card" key={medication.id}>
                <header>
                  <span className="gmus-code">{medication.codigo_gmus}</span>
                  <button
                    className="comparison-remove-button"
                    type="button"
                    onClick={() => removeMedication(medication.id)}
                    aria-label={`Remover ${medication.descricao} da comparação`}
                    title="Remover da comparação"
                  >
                    <X size={16} />
                  </button>
                </header>
                <div className="medication-comparison-card__title">
                  <span aria-hidden="true"><Pill size={18} /></span>
                  <h2>{medication.descricao}</h2>
                </div>
                <MedicationCategoryBadges medication={medication} />
                <dl>
                  <div>
                    <dt>Unidade</dt>
                    <dd>{medication.unidade || "Não informada"}</dd>
                  </div>
                  <div>
                    <dt>Estoque total</dt>
                    <dd>
                      {stockQuantityText(medication.quantidade_estoque_total)}
                      {medication.quantidade_estoque_total !== null && medication.unidade && (
                        <small>{medication.unidade}</small>
                      )}
                    </dd>
                  </div>
                </dl>
                <section className="comparison-ups" aria-label="Distribuição por UPS">
                  <h3>Quantidade por UPS</h3>
                  {competence ? (
                    <ul>
                      {ups.map((upsItem) => {
                        const stock = medication.estoque_por_ups.find(
                          (item) => item.ups_id === upsItem.id,
                        );
                        return (
                          <li key={upsItem.id}>
                            <span>
                              {upsItem.nome}
                              <small>Unidade G-MUS {upsItem.id_unidade_gmus}</small>
                            </span>
                            <strong>
                              {stockQuantityText(stock?.quantidade ?? "0.000")}
                              {medication.unidade && <small>{medication.unidade}</small>}
                            </strong>
                          </li>
                        );
                      })}
                    </ul>
                  ) : (
                    <p>Não informado</p>
                  )}
                </section>
                <Link
                  className="medication-card__detail-link"
                  to={`/admin/medicamentos/${medication.id}`}
                >
                  Abrir detalhe
                  <ArrowRight size={15} />
                </Link>
              </article>
            ))}
          </section>
        </>
      )}
    </main>
  );
}

export default MedicamentosCompararPage;
