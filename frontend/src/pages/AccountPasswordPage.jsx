import PasswordChangeCard from "../components/PasswordChangeCard";

function AccountPasswordPage() {
  return (
    <main className="staff-page account-password-page">
      <header className="page-heading">
        <div>
          <span className="eyebrow">Minha conta</span>
          <h1>Redefinir senha</h1>
          <p>Atualize a senha usada para acessar o StockFlow.</p>
        </div>
      </header>
      <PasswordChangeCard />
    </main>
  );
}

export default AccountPasswordPage;
