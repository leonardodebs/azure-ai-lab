# Deploy e Rollback de Serviços ECS

## Objetivo
Procedimento para realizar deploys e rollbacks seguros de serviços rodando em
Amazon ECS (Fargate ou EC2 launch type).

## 1. Estratégia de deploy
O ECS usa rolling update por padrão, controlado por `minimumHealthyPercent` e
`maximumPercent`. Para deploy sem downtime, mantenha `minimumHealthyPercent=100` e
`maximumPercent=200`, permitindo que novas tasks subam antes das antigas saírem.

## 2. Executando o deploy
1. Publique a nova imagem no ECR com uma tag imutável (ex: o SHA do commit).
2. Registre uma nova revisão da Task Definition apontando para a nova imagem.
3. Atualize o serviço: `aws ecs update-service --cluster X --service Y
   --task-definition Y:NOVA_REVISAO`.
4. Acompanhe o rollout em Events do serviço e no Target Group do ALB.

## 3. Rollback de ECS
O rollback no ECS é feito apontando o serviço para a revisão anterior da Task
Definition (que permanece registrada):

1. Liste as revisões: `aws ecs list-task-definitions --family-prefix Y`.
2. Atualize o serviço para a revisão anterior estável.
3. O ECS faz rolling update reverso, subindo tasks da versão antiga.

Diferença para o AKS (Kubernetes): no AKS o rollback usa `kubectl rollout undo
deployment/Y`, que reverte para o ReplicaSet anterior. O ECS reverte por Task
Definition; o AKS por ReplicaSet/Deployment revision. O conceito é o mesmo
(versão imutável anterior), mas o objeto versionado difere.

## 4. Health checks e estabilização
Configure o `healthCheckGracePeriodSeconds` para dar tempo da aplicação iniciar
antes do ALB marcar a task como unhealthy e o ECS reiniciá-la em loop.
