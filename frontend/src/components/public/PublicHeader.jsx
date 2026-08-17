import { Building2, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";

import { Brand } from "../Brand";

function PublicHeader() {
  return (
    <header className="public-header">
      <div className="public-header__inner">
        <Brand />
        <div className="public-header__context">
          <span>
            <Building2 size={15} aria-hidden="true" />
            Farmácia Municipal de Ribeirão Claro
          </span>
          <Link to="/login">
            <LockKeyhole size={14} aria-hidden="true" />
            Acesso administrativo
          </Link>
        </div>
      </div>
    </header>
  );
}

export default PublicHeader;
