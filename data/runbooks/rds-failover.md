# Failover de Banco de Dados RDS Multi-AZ

## Objetivo
Passos para diagnosticar e executar failover de uma instância Amazon RDS
configurada com Multi-AZ, além de validar a recuperação.

## 1. Como o Multi-AZ funciona
Em Multi-AZ, o RDS mantém uma réplica standby síncrona em outra Availability Zone.
Em caso de falha da instância primária, o RDS promove automaticamente o standby e
atualiza o DNS do endpoint para apontar para o novo primário (RTO típico de 60-120s).

## 2. Disparando um failover manual
Para testes de DR ou manutenção, force o failover:

1. `aws rds reboot-db-instance --db-instance-identifier X --force-failover`.
2. O endpoint DNS permanece o mesmo; apenas o IP por trás muda.
3. Aplicações devem reconectar; garanta que o pool de conexões tenha timeout e
   retry para reabrir conexões após a troca de DNS.

## 3. RTO e RPO
- **RTO (Recovery Time Objective)**: tempo máximo aceitável de indisponibilidade.
  No Multi-AZ síncrono, fica em torno de 1-2 minutos.
- **RPO (Recovery Point Objective)**: perda máxima aceitável de dados. Com réplica
  síncrona, o RPO é próximo de zero (sem perda de transações confirmadas).

## 4. Validação pós-failover
1. Confirme que a aplicação reconectou e está servindo queries.
2. Verifique a métrica `CloudWatch` de `DatabaseConnections` e latência.
3. Revise os Events do RDS para confirmar a AZ atual do primário.
