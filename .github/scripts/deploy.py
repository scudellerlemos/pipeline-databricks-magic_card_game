#!/usr/bin/env python3
"""
Script para deploy do pipeline no Databricks
"""

import yaml
import json
import subprocess
import sys
import os

def convert_yaml_to_json():
    """Converte YAML para JSON"""
    try:
        print("📖 Lendo arquivo YAML...")
        with open('.github/DAGs/magic.yml', 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        print(f"✅ YAML data loaded: {type(yaml_data)}")
        
        # Convert to JSON
        print("🔄 Convertendo para JSON...")
        json_content = json.dumps(yaml_data, indent=2, ensure_ascii=False)
        
        # Write JSON file
        with open('magic.json', 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        print(f"✅ JSON file written: {len(json_content)} characters")
        return True
        
    except Exception as e:
        print(f"❌ Erro na conversão: {e}")
        return False

def get_existing_job_id():
    """Obtém o ID do job existente se houver"""
    try:
        result = subprocess.run(
            ['databricks', 'jobs', 'list', '--output', 'JSON'],
            capture_output=True,
            text=True,
            check=True
        )
        
        jobs_data = json.loads(result.stdout)
        for job in jobs_data.get('jobs', []):
            if job.get('settings', {}).get('name') == 'MTG_PIPELINE':
                return job.get('job_id')
        
        return None
        
    except Exception as e:
        print(f"⚠️ Erro ao listar jobs: {e}")
        return None

def deploy_job():
    """Faz o deploy do job"""
    try:
        # Convert YAML to JSON
        if not convert_yaml_to_json():
            return False
        
        # Check if job exists
        job_id = get_existing_job_id()
        
        if job_id:
            print(f"🔄 Atualizando job existente ID: {job_id}")
            result = subprocess.run(
                ['databricks', 'jobs', 'reset', '--job-id', str(job_id), '--json', '@magic.json'],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Job atualizado com sucesso!")
        else:
            print("🆕 Criando novo job...")
            result = subprocess.run(
                ['databricks', 'jobs', 'create', '--json', '@magic.json'],
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Job criado com sucesso!")
        
        print(f"📄 Resposta: {result.stdout}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro no deploy: {e}")
        print(f"📄 stdout: {e.stdout}")
        print(f"📄 stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Iniciando deploy do pipeline...")
    success = deploy_job()
    
    if success:
        print("🎉 Deploy concluído com sucesso!")
        sys.exit(0)
    else:
        print("💥 Falha no deploy!")
        sys.exit(1) 