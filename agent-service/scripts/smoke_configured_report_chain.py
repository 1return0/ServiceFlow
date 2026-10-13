"""Real Java login/model/pgvector/report/SSH-Docker; only own QA account is mutated."""
import argparse
import io
import json
from pathlib import Path
import secrets
import sys
from uuid import uuid4
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    from app.config import load_settings
    settings=load_settings()
    from app.main import app
    from fastapi.testclient import TestClient
    import bcrypt,httpx,psycopg
    from psycopg.conninfo import make_conninfo
    from dotenv import dotenv_values
    business=dotenv_values(ROOT.parent/"business-service/.env")
    business_dsn=make_conninfo(host=business["EDUOPS_DB_HOST"],
        port=business.get("EDUOPS_DB_PORT") or "5432",dbname=business["EDUOPS_DB_NAME"],
        user=business["EDUOPS_DB_USERNAME"],password=business["EDUOPS_DB_PASSWORD"])
    account_id=uuid4()
    username="reportqa_"+uuid4().hex[:20]
    password=secrets.token_urlsafe(24)
    with psycopg.connect(business_dsn) as connection:
        connection.execute("INSERT INTO account_user(id,username,password_hash,role_code,enabled) VALUES(%s,%s,%s,'STUDENT',TRUE)",
            (account_id,username,bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode()))
    document_id=None
    checks=[]
    observed=[]
    try:
        with httpx.Client(trust_env=False,timeout=10) as http:
            login=http.post(settings.business_service_base_url+"/api/v1/auth/login",json={"username":username,"password":password})
            assert login.status_code==200,"real-java-login-failed"
            token=login.json()["data"]["accessToken"]
        checks.append("real-java-login-jwt")
        headers={"Authorization":"Bearer "+token}
        with TestClient(app) as client:
            runtime=app.state.campus_support_triage_runtime
            original=runtime.invoke
            def record_call(**kwargs):
                result=original(**kwargs)
                answer=result.get("knowledge_answer")
                observed.append({"jwt_passed_to_generator":kwargs.get("authorization") is not None,
                                 "answer_model_called":bool(answer and answer.model_called)})
                if answer:
                    from urllib.parse import urlsplit
                    print(json.dumps({"answer_status":answer.status,"citation_schemes":
                        [urlsplit(c.source_reference).scheme for c in answer.citations],
                        "answer_chars":len(answer.answer_text)}))
                return result
            runtime.invoke=record_call
            try:
                invalid=client.get("/api/v1/knowledge/reports",headers={"Authorization":"Bearer invalid-test-token"})
                assert invalid.status_code==401
                checks.append("invalid-jwt-rejected")
                result=client.post("/api/v1/knowledge/reports",headers=headers,
                    json={"query":"校园网无法连接时应该怎么办？","title":"真实校园知识报告"})
                assert result.status_code==201,f"report-generation-failed:{result.status_code}:{result.json().get('detail')}"
                document=result.json()
                document_id=document["document_id"]
                assert observed[-1]=={"jwt_passed_to_generator":False,"answer_model_called":True}
                checks.append("real-public-graph-model-pgvector-report")
                proposal=client.post(f"/api/v1/knowledge/reports/{document_id}/proposals",headers=headers,
                    json={"base_revision":1,"title":"校园知识确认版"})
                assert proposal.status_code==201
                confirmed=client.post(f"/api/v1/knowledge/reports/{document_id}/proposals/{proposal.json()['proposal_id']}/confirm",headers=headers,
                    json={"user_confirmed":True})
                assert confirmed.status_code==200 and confirmed.json()["revision"]==2
                checks.append("postgres-version-confirmation")
                exported=client.post(f"/api/v1/knowledge/reports/{document_id}/export",headers=headers,
                    json={"expected_revision":2,"user_confirmed":True})
                assert exported.status_code==200,f"ssh-docker-export-failed:{exported.status_code}"
                with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
                    assert "校园知识确认版" in archive.read("word/document.xml").decode()
                checks.append("ssh-docker-docx")
                report={"status":"passed","checks":checks,"docx_bytes":len(exported.content),
                    "export_backend":"ssh_docker","public_generation":observed,
                    "boundary":"Real Java HTTP authentication and JWT verification, Python in-process HTTP, model/pgvector/PG report/SSH Docker. No RabbitMQ, browser, load or production SLA claim."}
            finally:
                runtime.invoke=original
                if document_id:
                    assert client.delete(f"/api/v1/knowledge/reports/{document_id}",headers=headers).status_code==204
    finally:
        with psycopg.connect(business_dsn) as connection:
            connection.execute("DELETE FROM account_user WHERE id=%s AND username=%s",(account_id,username))
    report["cleanup"]="own temporary account, report, revisions and proposals removed"
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
