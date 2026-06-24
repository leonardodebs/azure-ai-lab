# Diagnóstico de Conectividade em VPC

## Objetivo
Guia para diagnosticar problemas de conectividade de rede dentro de uma VPC AWS,
cobrindo subnets, route tables, NAT e Internet Gateway.

## 1. NAT Gateway vs Internet Gateway
- **Internet Gateway (IGW)**: dá acesso bidirecional à internet para recursos em
  subnets públicas (que têm IP público). É o caminho de entrada e saída.
- **NAT Gateway**: permite que recursos em subnets privadas iniciem conexões de
  SAÍDA para a internet (ex: baixar pacotes), sem aceitar conexões de entrada.

Uma subnet é "pública" quando sua route table tem rota `0.0.0.0/0` para um IGW.
Uma subnet "privada" roteia `0.0.0.0/0` para um NAT Gateway.

## 2. Checklist de conectividade
1. A route table da subnet tem a rota correta (IGW para pública, NAT para privada)?
2. O Security Group permite o tráfego desejado (regras de entrada/saída)?
3. A Network ACL da subnet não está bloqueando (lembre que NACLs são stateless)?
4. O recurso em subnet pública tem realmente um IP público associado?
5. Para conectar a outra VPC, há VPC Peering ou Transit Gateway com rotas válidas?

## 3. Riscos de segurança em VPC pública
- Exposição de portas administrativas (SSH 22, RDP 3389) ao `0.0.0.0/0`
- Security Groups permissivos demais (qualquer porta para qualquer origem)
- Falta de segmentação entre camadas (web/app/banco na mesma subnet)
- Ausência de VPC Flow Logs para auditoria de tráfego
- Credenciais IAM em instâncias em vez de IAM Roles
