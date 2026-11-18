import { defineRailway, project, service } from 'railway/iac'

export const partial = 'wallnut'

export default defineRailway(() => project('wallnut', {
  variables: { managed: false },
  resources: [service('wallnut', {
    build: { builder: 'DOCKERFILE', dockerfilePath: 'Dockerfile' },
    healthcheck: '/v1/ready',
    healthcheckTimeout: 120,
  })],
}))
