import pandas as pd, numpy as np, json, sys, country_converter as coco
RAW='raw'; OUT='.'  # raw/qcl.csv = descarga filtrada; raw/fbs/ = zip del balance descomprimido
st={}
cc=coco.CountryConverter()
CONT={'Africa':'África','America':'América','Asia':'Asia','Europe':'Europa','Oceania':'Oceanía'}

# ---------- PRODUCCION (QCL) ----------
q=pd.read_csv(f'{RAW}/qcl.csv',encoding='utf-8-sig')
st['qcl_filas_orig']=len(q); st['qcl_cols_orig']=q.shape[1]
st['qcl_paises_orig']=q['Área'].nunique()
st['qcl_simbolos']=q['Símbolo'].value_counts().to_dict()
grupo_q={'Cereales, primarios':'Cereales','Frutas Primaria':'Frutas','Hortaliz Prim Exc Melon':'Verduras',
 'Raíces&Tubérculos, total':'Raíces y tubérculos','Carne, total':'Carne','Leche, total':'Leche','Huevos Naturales':'Huevos'}
q=q.rename(columns={'Código del área (ISO3)':'iso3','Área':'pais','Producto':'producto_fao','Año':'anio','Valor':'toneladas','Símbolo':'simbolo'})
q['grupo']=q.producto_fao.map(grupo_q)
# China agregado (F351) duplica a China continental + Taiwán + HK + Macao
st['qcl_china_agregado_filas']=int((q.iso3=='F351').sum())
q=q[q.iso3!='F351']
st['qcl_nulos']=int(q.toneladas.isna().sum())
st['qcl_nulos_detalle']=q[q.toneladas.isna()].groupby(['pais','grupo']).size().reset_index(name='n').to_dict('records')
st['qcl_ceros']=int((q.toneladas==0).sum())
q=q[q.toneladas.notna()]
prod=q[['iso3','pais','grupo','anio','toneladas','simbolo']].copy()

# ---------- BALANCES (FBS) ----------
f=pd.read_csv(f'{RAW}/fbs/FoodBalanceSheets_E_All_Data.csv',encoding='latin1')
st['fbs_filas_orig']=len(f); st['fbs_cols_orig']=f.shape[1]
st['fbs_areas_orig']=f['Area Code'].nunique(); st['fbs_agregados']=int(f[f['Area Code']>=5000]['Area Code'].nunique())
st['fbs_productos_orig']=f.Item.nunique(); st['fbs_elementos_orig']=f.Element.nunique()
f=f[f['Area Code']<5000]          # quitar regiones/agregados
f=f[f['Area Code']!=351]          # China agregado
items={'Population':'Población','Grand Total':'Total general','Vegetal Products':'Productos vegetales','Animal Products':'Productos animales',
 'Cereals - Excluding Beer':'Cereales','Starchy Roots':'Raíces y tubérculos','Vegetables':'Verduras','Fruits - Excluding Wine':'Frutas',
 'Meat':'Carne','Eggs':'Huevos','Milk - Excluding Butter':'Leche'}
elems={'Total Population - Both sexes':'Población total','Production':'Producción','Import quantity':'Importación','Export quantity':'Exportación',
 'Stock Variation':'Variación de existencias','Domestic supply quantity':'Suministro interno','Food':'Alimento','Feed':'Piensos','Seed':'Semilla',
 'Losses':'Pérdidas','Processing':'Procesado','Other uses (non-food)':'Otros usos','Tourist consumption':'Consumo turístico','Residuals':'Residuales',
 'Food supply (kcal/capita/day)':'kcal/cápita/día','Food supply quantity (kg/capita/yr)':'kg/cápita/año'}
st['fbs_items_duplicados']='Eggs (2744) y Milk - Excluding Butter (2848) repiten nombre del agregado; se conservan solo 2949 y 2948'
f=f[~f['Item Code'].isin([2744,2848])]
f=f[f.Item.isin(items)&f.Element.isin(elems)]
yrs=list(range(2015,2024))
vals=f.melt(id_vars=['Area Code (M49)','Area','Item','Element','Unit'],value_vars=[f'Y{y}' for y in yrs],var_name='y',value_name='valor')
flg=f.melt(id_vars=['Area Code (M49)','Area','Item','Element'],value_vars=[f'Y{y}F' for y in yrs],var_name='y',value_name='simbolo')
vals['anio']=vals.y.str[1:].astype(int); flg['anio']=flg.y.str[1:5].astype(int)
b=vals.drop(columns='y').merge(flg.drop(columns='y'),on=['Area Code (M49)','Area','Item','Element','anio'])
b['m49']=b['Area Code (M49)'].str.strip("'").astype(int)
st['fbs_unidades']=b.Unit.value_counts().to_dict()
# unidades: 1000 t -> t ; 1000 No -> personas
b.loc[b.Unit=='1000 t','valor']*=1000; b.loc[b.Unit=='1000 t','Unit']='t'
b.loc[b.Unit=='1000 No','valor']*=1000; b.loc[b.Unit=='1000 No','Unit']='personas'
b['grupo']=b.Item.map(items); b['elemento']=b.Element.map(elems)
b['iso3']=cc.pandas_convert(b.m49.astype(str),src='UNcode',to='ISO3',not_found=None)
b.loc[b.m49==158,'iso3']='TWN'
st['fbs_nulos']=int(b.valor.isna().sum())
st['fbs_simbolos']=b.simbolo.value_counts(dropna=False).to_dict()
bal=b[b.valor.notna()][['iso3','Area','grupo','elemento','anio','valor','Unit','simbolo']].rename(columns={'Area':'pais_en','Unit':'unidad'})

# ---------- PAISES / CONTINENTES ----------
isos=sorted(set(prod.iso3)|set(bal.iso3))
pa=pd.DataFrame({'iso3':isos})
pa['continente']=cc.pandas_convert(pa.iso3,src='ISO3',to='continent').map(CONT)
pa.loc[pa.iso3=='TWN','continente']='Asia'
pa['subregion']=cc.pandas_convert(pa.iso3,src='ISO3',to='UNregion')
pa.loc[pa.iso3=='TWN','subregion']='Eastern Asia'
nom=prod.drop_duplicates('iso3').set_index('iso3').pais
pa['pais']=pa.iso3.map(nom)
fb_en=bal.drop_duplicates('iso3').set_index('iso3').pais_en
pa['pais']=pa.pais.fillna(pa.iso3.map(fb_en))
st['paises_sin_continente']=pa[pa.continente.isna()].to_dict('records')
pa=pa[['iso3','pais','continente','subregion']]
st['paises_total']=len(pa); st['paises_qcl']=prod.iso3.nunique(); st['paises_fbs']=bal.iso3.nunique()
st['paises_solo_qcl']=sorted(pa[pa.iso3.isin(set(prod.iso3)-set(bal.iso3))].pais.tolist())
bal=bal.merge(pa[['iso3','pais']],on='iso3').drop(columns='pais_en')

prod.to_csv(f'{OUT}/produccion.csv',index=False)
bal[['iso3','pais','grupo','elemento','anio','valor','unidad','simbolo']].to_csv(f'{OUT}/balance_alimentario.csv',index=False)
pa.to_csv(f'{OUT}/paises.csv',index=False)
st['prod_filas']=len(prod); st['bal_filas']=len(bal); st['bal_dup']=int(bal.duplicated(['iso3','grupo','elemento','anio']).sum())
json.dump(st,open('stats_limpieza.json','w'),ensure_ascii=False,indent=1,default=str)
print(json.dumps(st,ensure_ascii=False,indent=1,default=str)[:4000])

# ---------- marcar variaciones atipicas (no se eliminan) ----------
p=pd.read_csv(f'{OUT}/produccion.csv').sort_values(['iso3','grupo','anio'])
prev=p.groupby(['iso3','grupo']).toneladas.shift()
p['variacion_atipica']=((prev>100000)&((p.toneladas/prev-1).abs()>0.5)).astype(int)
p.to_csv(f'{OUT}/produccion.csv',index=False)
print('atipicos',p.variacion_atipica.sum())
