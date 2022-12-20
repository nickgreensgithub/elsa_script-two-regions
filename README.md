## Input
```
<chr##>  <label> <start>   <end>  
```
ie.
```
chr02  CR         39673000   39673200
chr02  PS39673005 39673005   39673085  
chr02  PS39673086 39673086   39673098  
chr02  PS39673005 39673099   39673191
```

If a region is covered by `CR` and by another sequence then the other sequence takes precedence

## Graphical representation

Turns this:

```
|------------CR------------|
|-----1-----|  
    |--2--| 
            |--3--|
                |--4--|
```

Into this:

```
|-1-|     |1|  
    |--2--| 
            |-3-|
                |--4--|
                       |-CR-|                
```
