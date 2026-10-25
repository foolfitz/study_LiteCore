"""Finite synchronous Q restoration cohort, registered before counted execution."""
D_ARMS=[]
for label,fixture in (("plain","plain3"),("numbered","numbered-second"),("indent","indent-second")):
    for variant,ops in (("direct","K1283"),("restore","K5122;Qbefore;K1283"),("wrong-line","K5122;Qwrong;K1283")):
        D_ARMS.append({"name":f"delete-{label}-{variant}","fixture":fixture,
                       "script":f"rwrong,k1024,k1028,rbefore,Xdelete@1028={ops},S,L",
                       "note":f"synchronous Q restoration: {label}, {variant}","decides":True})
