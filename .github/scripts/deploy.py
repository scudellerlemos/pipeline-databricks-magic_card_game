#!/usr/bin/env python3
"""
Script para deploy do pipeline no Databricks
"""

import yaml
import json
import subprocess
import sys
import os
from datetime import datetime

def log(message, level="INFO"):
    """Função para logging padronizado"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def convert_yaml_to_json():
    """Converte YAML para JSON"""
    try:
        log("📖 Lendo arquivo YAML...")
        with open('.github/DAGs/magic.yml', 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        
        log(f"✅ YAML data loaded: {type(yaml_data)}")
        
        # Validate required structure
        if 'resources' not in yaml_data or 'jobs' not in yaml_data['resources']:
            log("❌ Estrutura YAML inválida: resources.jobs não encontrado", "ERROR")
            return False
            
        if 'MTG_PIPELINE' not in yaml_data['resources']['jobs']:
            log("❌ Job MTG_PIPELINE não encontrado na configuração", "ERROR")
            return False
        
        # Convert to JSON
        log("🔄 Convertendo para JSON...")
        json_content = json.dumps(yaml_data, indent=2, ensure_ascii=False)
        
        # Write JSON file
        with open('magic.json', 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        log(f"✅ JSON file written: {len(json_content)} characters")
        return True
        
    except Exception as e:
        log(f"❌ Erro na conversão: {e}", "ERROR")
        return False

def get_existing_job_id():
    """Obtém o ID do job existente se houver"""
    try:
        log("🔍 Verificando jobs existentes...")
        
        # Try with JSON output first (new CLI)
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
                    job_id = job.get('job_id')
                    log(f"✅ Job existente encontrado: ID {job_id}")
                    return job_id
            
        except subprocess.CalledProcessError:
            # Fallback for old CLI version without --output flag
            log("⚠️ CLI antiga detectada, listando jobs sem --output flag...")
            result = subprocess.run(
                ['databricks', 'jobs', 'list'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse text output to find MTG_PIPELINE
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if 'MTG_PIPELINE' in line:
                    # Extract job ID from text output (format: "123 MTG_PIPELINE")
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] == 'MTG_PIPELINE':
                        job_id = parts[0]
                        log(f"✅ Job existente encontrado: ID {job_id}")
                        return job_id
        
        log("ℹ️ Nenhum job existente encontrado, será criado um novo")
        return None
        
    except subprocess.CalledProcessError as e:
        log(f"⚠️ Erro ao listar jobs: {e.stderr}", "WARN")
        return None
    except Exception as e:
        log(f"⚠️ Erro inesperado ao listar jobs: {e}", "WARN")
        return None

def validate_databricks_connection():
    """Valida a conexão com o Databricks"""
    try:
        log("🔗 Testando conexão com Databricks...")
        result = subprocess.run(
            ['databricks', '--version'],
            capture_output=True,
            text=True,
            check=True
        )
        log(f"✅ Databricks CLI version: {result.stdout.strip()}")
        
        # Test workspace access (compatible with old CLI version)
        try:
            result = subprocess.run(
                ['databricks', 'workspace', 'list', '--output', 'JSON'],
                capture_output=True,
                text=True,
                check=True
            )
            log("✅ Conexão com workspace estabelecida (JSON output)")
        except subprocess.CalledProcessError:
            # Fallback for old CLI version without --output flag
            log("⚠️ CLI antiga detectada, testando sem --output flag...")
            result = subprocess.run(
                ['databricks', 'workspace', 'list'],
                capture_output=True,
                text=True,
                check=True
            )
            log("✅ Conexão com workspace estabelecida (text output)")
        
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"❌ Erro na conexão com Databricks: {e.stderr}", "ERROR")
        return False
    except Exception as e:
        log(f"❌ Erro inesperado na validação: {e}", "ERROR")
        return False

def deploy_job():
    """Faz o deploy do job"""
    try:
        # Validate connection first
        if not validate_databricks_connection():
            return False
        
        # Convert YAML to JSON
        if not convert_yaml_to_json():
            return False
        
        # Check if job exists
        job_id = get_existing_job_id()
        
        if job_id:
            log(f"🔄 Atualizando job existente ID: {job_id}")
            result = subprocess.run(
                ['databricks', 'jobs', 'reset', '--job-id', str(job_id), '--json', '@magic.json'],
                capture_output=True,
                text=True,
                check=True
            )
            log("✅ Job atualizado com sucesso!")
        else:
            log("🆕 Criando novo job...")
            result = subprocess.run(
                ['databricks', 'jobs', 'create', '--json', '@magic.json'],
                capture_output=True,
                text=True,
                check=True
            )
            log("✅ Job criado com sucesso!")
        
        log(f"📄 Resposta do Databricks: {result.stdout}")
        
        # Parse response to get job ID
        try:
            response_data = json.loads(result.stdout)
            new_job_id = response_data.get('job_id')
            if new_job_id:
                log(f"🎯 Job ID: {new_job_id}")
        except:
            log("⚠️ Não foi possível extrair o Job ID da resposta", "WARN")
        
        return True
        
    except subprocess.CalledProcessError as e:
        log(f"❌ Erro no deploy: {e}", "ERROR")
        log(f"📄 stdout: {e.stdout}", "DEBUG")
        log(f"📄 stderr: {e.stderr}", "ERROR")
        return False
    except Exception as e:
        log(f"❌ Erro inesperado: {e}", "ERROR")
        return False

def verify_deployment():
    """Verifica se o deploy foi bem-sucedido"""
    try:
        log("🔍 Verificando deploy...")
        sleep_time = 30
        log(f"⏳ Aguardando {sleep_time} segundos para verificação...")
        
        import time
        time.sleep(sleep_time)
        
        # Try with JSON output first (new CLI)
        try:
            result = subprocess.run(
                ['databricks', 'jobs', 'list', '--output', 'JSON'],
                capture_output=True,
                text=True,
                check=True
            )
            
            jobs_data = json.loads(result.stdout)
            mtg_job = None
            
            for job in jobs_data.get('jobs', []):
                if job.get('settings', {}).get('name') == 'MTG_PIPELINE':
                    mtg_job = job
                    break
            
            if mtg_job:
                job_id = mtg_job.get('job_id')
                status = mtg_job.get('settings', {}).get('schedule', {}).get('pause_status', 'UNKNOWN')
                log(f"✅ Job verificado - ID: {job_id}, Status: {status}")
                
                # Log job details
                log("📊 Detalhes do Job:")
                log(f"  - Nome: {mtg_job.get('settings', {}).get('name')}")
                log(f"  - Descrição: {mtg_job.get('settings', {}).get('description', 'N/A')}")
                log(f"  - Status do Schedule: {status}")
                log(f"  - Total de Tasks: {len(mtg_job.get('settings', {}).get('tasks', []))}")
                
                return True
            else:
                log("❌ Job não encontrado após deploy", "ERROR")
                return False
                
        except subprocess.CalledProcessError:
            # Fallback for old CLI version without --output flag
            log("⚠️ CLI antiga detectada, verificando sem --output flag...")
            result = subprocess.run(
                ['databricks', 'jobs', 'list'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse text output to find MTG_PIPELINE
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                if 'MTG_PIPELINE' in line:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] == 'MTG_PIPELINE':
                        job_id = parts[0]
                        log(f"✅ Job verificado - ID: {job_id}")
                        log("📊 Detalhes do Job:")
                        log(f"  - Nome: MTG_PIPELINE")
                        log(f"  - ID: {job_id}")
                        log("  - Status: Verificado via CLI antiga")
                        return True
            
            log("❌ Job não encontrado após deploy", "ERROR")
            return False
            
    except Exception as e:
        log(f"❌ Erro na verificação: {e}", "ERROR")
        return False

def cleanup():
    """Limpa arquivos temporários"""
    try:
        if os.path.exists('magic.json'):
            os.remove('magic.json')
            log("🧹 Arquivo temporário removido")
    except Exception as e:
        log(f"⚠️ Erro na limpeza: {e}", "WARN")

if __name__ == "__main__":
    log("🚀 Iniciando deploy do pipeline...")
    log("=" * 60)
    
    try:
        # Deploy the job
        deploy_success = deploy_job()
        
        if deploy_success:
            log("✅ Deploy executado com sucesso!")
            
            # Verify deployment
            verify_success = verify_deployment()
            
            if verify_success:
                log("🎉 Deploy e verificação concluídos com sucesso!")
                log("=" * 60)
                sys.exit(0)
            else:
                log("⚠️ Deploy executado mas verificação falhou", "WARN")
                log("=" * 60)
                sys.exit(1)
        else:
            log("💥 Falha no deploy!", "ERROR")
            log("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        log("⚠️ Deploy interrompido pelo usuário", "WARN")
        sys.exit(1)
    except Exception as e:
        log(f"💥 Erro crítico: {e}", "ERROR")
        sys.exit(1)
    finally:
        cleanup() 