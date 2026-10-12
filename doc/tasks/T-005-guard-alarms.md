# T-005: Guard alarms and budget

- Status: ready
- Roadmap phase: 5 (pulled forward: monitoring part only)
- Branch: feat/T-005-guard-alarms
- Requested: owner, 2026-10-12 („priprav strážne alarmy na backende“)

## Goal
The owner gets an e-mail when the public lead API breaks, is abused or starts costing money, without
watching the console. Everything is defined in `template.yaml` and deployed by the GitHub pipeline.

## Context
- `POST /leads` is public and live since T-004 (website form connected). Throttling is 5 req/s per method.
- A lead is stored even when the SES notification fails (`src/leads/notifier.py` logs
  `Lead notification failed: lead_id=… error=…`). Today nobody would notice: the lead sits in DynamoDB unseen.
- Deploys run only from GitHub Actions with role `inocube-web-github-deploy` and policy
  `InocubeWebSamDeploy` (`doc/aws/inocube-web-sam-deploy-policy.json`, ADR 0011, ADR 0012). That policy has
  no CloudWatch alarm, SNS, metric filter or Budgets actions yet, so the owner must update it before merge.
- Agents never touch AWS (ADR 0011). Nothing in this task is run against AWS by the implementer.
- Recipient: `inocube@varga.slmail.me` (SimpleLogin alias forwarding to Proton Mail).

## Scope
1. Parameter `AlarmEmail` (default `inocube@varga.slmail.me`, same pattern as `NotifyEmail`).
2. SNS topic `${AWS::StackName}-alarms` with an e-mail subscription to `AlarmEmail`. Alarms send on ALARM
   and on OK (so the owner also learns that it recovered).
3. CloudWatch alarms, names prefixed `${AWS::StackName}-`, 5-minute periods, `TreatMissingData: notBreaching`
   (no traffic is normal for this site):
   - `leads-errors`: `AWS/Lambda Errors` of `LeadsFunction`, Sum ≥ 1.
   - `health-errors`: same for `HealthFunction`.
   - `lambda-throttles`: `AWS/Lambda Throttles` of both functions (metric math or two alarms), Sum ≥ 1.
   - `leads-duration`: `LeadsFunction` `Duration` Maximum ≥ 12000 ms (timeout is 15 s).
   - `api-5xx`: `AWS/ApiGateway 5XXError` of the API (`ApiName` + `Stage` Prod), Sum ≥ 1.
   - `api-traffic-spike`: `AWS/ApiGateway Count`, Sum > `ApiRequestsAlarmThreshold` (parameter, default 300
     per 5 min). Catches bots/abuse well below the throttle ceiling and cost growth.
   - `leads-notification-failed`: `AWS::Logs::MetricFilter` on `LeadsLogGroup`, pattern
     `"Lead notification failed"`, metric `LeadNotificationFailed` in namespace `Inocube/Backend` (value 1,
     default 0); alarm Sum ≥ 1. The alarm text tells the owner to look in DynamoDB for the unseen lead.
   - `dynamodb-errors`: `AWS/DynamoDB` `SystemErrors` or `ThrottledRequests` on `inocube-leads`, Sum ≥ 1.
   Every alarm has an `AlarmDescription` in plain English saying what it means and what to check first.
4. `AWS::Budgets::Budget` `${AWS::StackName}-monthly`, COST, MONTHLY, parameter `MonthlyBudgetUsd`
   (default 5). Notifications by e-mail to `AlarmEmail`: ACTUAL > 80 %, FORECASTED > 100 %.
   Note: the budget is account-wide (all services), which is what the owner wants.
5. `doc/aws/inocube-web-sam-deploy-policy.json`: add the narrowest actions the deploy needs, scoped by ARN:
   CloudWatch alarms `arn:aws:cloudwatch:eu-central-1:754895435437:alarm:inocube-backend-*`, SNS topic
   `arn:aws:sns:eu-central-1:754895435437:inocube-backend-*`, metric filters on the existing
   `/aws/lambda/inocube-backend-*` log groups, Budgets `arn:aws:budgets::754895435437:budget/inocube-backend-*`.
   Check which actions CloudFormation actually calls for each resource type (create, update, delete, tag,
   describe) and list them; no `*` actions. The Lambda boundary should not need changes; say so if it does.
6. Owner steps in this task (before merge: policy update; after merge: confirm the SNS subscription mail,
   optional test via `aws cloudwatch set-alarm-state`).
7. Docs: `doc/status.md`, `doc/architecture.md` (monitoring section), roadmap phase 5 note, README if it
   lists resources. PR "Why it is built this way": CloudWatch metrics vs alarms vs log metric filters, SNS,
   `TreatMissingData`, why Budgets is account-wide and delayed (~8-24 h), alarm costs.

## Acceptance criteria
- [ ] `sam validate --lint`, `ruff check`, `pytest` pass; `sam build` passes.
- [ ] All alarms, the topic, the metric filter and the budget are in `template.yaml`; nothing by hand.
- [ ] Every alarm uses the SNS topic for ALARM and OK, has a description and `TreatMissingData: notBreaching`.
- [ ] The deploy policy diff only adds actions, each scoped to `inocube-backend-*` ARNs where the service
      supports resource-level permissions; services that need `*` are justified in the PR.
- [ ] Metric filter pattern matches the exact log line from `notifier.py`; a unit test pins that log text
      so a future rename breaks the test, not the alarm silently.
- [ ] Monthly cost of the additions stated in the PR (alarms ~0.10 USD each, first 2 budgets free).
- [ ] Owner steps complete and in order.

## Out of scope
- Alarms on the frontend/Netlify, uptime checks from outside AWS, dashboards, PagerDuty/Slack.
- Custom domain, staging stack, SES production access, log Insights queries.
- Changing throttling or function code beyond the test in the acceptance criteria.

## Open questions
(none; owner can change thresholds later via parameters)

## Implementation notes
(implementer)

## Architect review
(architect: verdict approved / changes-requested, findings with file:line)
