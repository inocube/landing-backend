produkčný základ serverless backendu na AWS. Autentifikácia cez IAM Identity Center s dočasnými credentials namiesto dlhodobých kľúčov. Prvá Lambda v Pythone nasadená cez SAM/IaC, dostupná na verejnej HTTPS URL. Repo chránené branch protection rulesettom — priamy push do main je zablokovaný, všetko ide cez PR.

Hot Partition - riziko hot partition pri single-value GSI partition key, pri očakávanej záťaži rádovo jednotky leadov denne som zvolil jednoduchosť pred predčasnou optimalizáciou. Write sharding by som pridal, keby záťaž rástla k stovkám requestov za sekundu.
