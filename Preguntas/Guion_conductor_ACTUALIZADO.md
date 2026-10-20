# CHICOS VS CHICAS — ¿Quién sabe más?
## Guion del conductor · actualizado desde `preguntas_banco.json` (programa, puerto 8769)
Documento privado: contiene todas las respuestas. No lo compartas con los participantes.

> Sincronizado con el banco del 18/10/2026. Corrige al PDF viejo `Chicos_VS_Chicas_CONDUCTOR_sin_rebote.pdf`.
> Cambios grandes vs PDF viejo: **Saltar ya no existe → es DOBLE O NADA (+3/−1)**; **Matemáticas salió de R3 y es ronda propia por aproximación**;
> **R3 tiene 3 temas (Minecraft, Cine y series, Cultura y arte)** con preguntas nuevas;
> **el REBOTE es SOLO de la final** (en R4 ya no rebota: falló y se revela, como cualquier ronda normal);
> **la final no lleva redoble**; **"segundos de luz del Sol" y "días de clase" pasaron de R4 a Matemáticas**;
> **la pregunta de "minutos en una semana" se movió a Matemáticas**; **Final pregunta 3 es "ardilla / Squirrel", NO "mariposa / Butterfly"**; **Desempate son 4, no 3**.

## 1. Ficha rápida

| Ronda | id | Tipo | Puntos | Tiempo | Comodines | Notas |
|---|---|---|---|---|---|---|
| Cultura general | r1 | opciones A-D | 1 | 20 s | llamada, saltar, cambiar, 5050 | — |
| Territorio enemigo | r2 | opciones A-D | 2 | 20 s | llamada, saltar, cambiar, 5050 | — |
| Elige tu tema | r3 | abierta | 1 | 20 s | llamada, saltar, cambiar | — |
| Matemáticas | mate | abierta | 1 | 40 s (60 s en la de la luz del Sol) | — | responden los DOS · por aproximación · sin comodines |
| Capciosas y lógica | r4 | abierta | 1 | 30 s (60 s en la de los gatos) | llamada, saltar, cambiar | sin rebote |
| Gran final | final | abierta | 2 | 10 s | — | si acierta sigue · CON REBOTE · sin comodines · sin redoble |
| Desempate | desempate | abierta | 1 | 10 s | — | sin comodines |

**Total:** 68 preguntas (incluidas reservas). Material: motor `preguntas_control.py` + overlay `preguntas-obs-local.html` (1920×1080, "Controlar el audio mediante OBS"), 2 celulares para llamadas, sonidos: usar, reactivar, inicio, campana, tictac, acierto, error, redoble.

## 2. Reglas y comodines (leer en la intro)

1. **Turnos:** en r1, r2, r3 y desempate alternan. En **Matemáticas** responden **LOS DOS equipos a la vez**. En **Capciosas** responde el equipo que indique el conductor (turno alternado).
2. **Puntos:** acierto suma los puntos de la ronda. Error o tiempo agotado: se revela y se sigue (salvo el rebote de la final).
3. **Sin ayuda externa:** solo comodines. Llamada en altavoz y a cámara, sin internet.
4. **Comodines:** cada equipo tiene 4 (uno de cada tipo), **solo 1 por pregunta**. Si no se puede aplicar, NO se gasta y el programa avisa. **En cada transición de ronda, recordar cuáles siguen valiendo** (ver avisos abajo).
5. **Revelado con redoble:** en TODAS las rondas **menos la final**, al pulsar Revelar suena el redoble (fase `revelando`, reloj pausado) y después se muestra la respuesta + acierto/error. Segundo clic corta el redoble y revela ya. **La final revela DIRECTO, sin tambores.**
6. **Rebote (SOLO la final):** si el equipo que responde **falla**, la MISMA pregunta pasa al otro equipo con el reloj de nuevo y **sin revelar**. Si el otro acierta, se lleva el punto. Si **fallan los dos**, se revela, no suma nadie, y la siguiente la empieza el que la había empezado. **En R4 no hay rebote:** si falla, se revela y sigue.

### Avisos del conductor entre rondas (comodines)

Decir algo así antes de cada transición, para que nadie se quede con un comodín vencido:

- Antes de **r2**: "Última ronda con **50/50**; después ya no vuelve a valer en ninguna otra."
- Antes de **r3**: "En esta ronda **no vale el 50/50** (son preguntas abiertas). Quedan válidos llamada, doble o nada y cambiar."
- Antes de **Matemáticas**: "**Se terminaron los comodines**: Matemáticas es sin ninguno. Si les quedó alguno, usenlo ahora o se pierde."
- Antes de **r4**: "Vuelven a valer **llamada, doble o nada y cambiar**. El 50/50 ya no vuelve más."
- Antes de la **final**: "**Última oportunidad:** la final es **sin comodines**. Son preguntas **rápidas: 10 segundos cada una, seguidas, sin pausas** entre ellas; y si el que responde falla, **la misma pregunta rebota al otro** con el reloj de nuevo."

### Los 4 comodines (nombre real en pantalla)

| Comodín | Cómo funciona |
|---|---|
| LLAMADA A UN AMIGO | 30 s por celular en altavoz. Después vuelve el reloj donde estaba. Si no contesta / no sirvió, el conductor puede **devolverla** (botón Devolver) y no se pierde |
| DOBLE O NADA (clave vieja "saltar") | **Ya NO salta pregunta.** Si acierta suma **3**, si falla resta **1** (el marcador no baja de 0). Se marca antes de revelar |
| CAMBIAR PREGUNTA | Cambia por reserva: usa una reserva libre de la ronda (en r2, del mismo equipo; en r3, del tema). Se marca antes de revelar |
| 50/50 | Quita dos opciones incorrectas (queda la correcta + 1). Solo en r1 y r2 (opciones) |

### Qué comodín vale en cada ronda

| Ronda | Válidos |
|---|---|
| Cultura general | llamada, saltar, cambiar, 5050 |
| Territorio enemigo | llamada, saltar, cambiar, 5050 |
| Elige tu tema | llamada, saltar, cambiar |
| Matemáticas | **NINGUNO** |
| Capciosas y lógica | llamada, saltar, cambiar |
| Gran final | **NINGUNO** |
| Desempate | **NINGUNO** |

## 3. Escaleta sugerida (ajustar a 60 min)

r1 → r2 → r3 (cada equipo elige 1 tema, 4 preguntas cada uno) → Matemáticas (los dos responden por aproximación, sin comodines) → r4 Capciosas (sin rebote) → final muerte súbita con rebote → desempate solo si empatan → cierre.

## 4. Cultura general (opciones, 1 pt, 20 s)
Comodines: llamada, **doble o nada** (antes "saltar"), cambiar, 50/50.

- ¿Cuál es la capital de Australia? — A) Sídney · B) Melbourne · **C) Canberra** · D) Perth
- ¿Cuál es el elemento más abundante del universo? — A) Oxígeno · **B) Hidrógeno** · C) Carbono · D) Helio
- ¿En qué año cayó el Muro de Berlín? — A) 1985 · B) 1987 · C) 1991 · **D) 1989**
- ¿Cuál es el hueso más largo del cuerpo humano? — **A) Fémur** · B) Tibia · C) Húmero · D) Peroné
- ¿Cuál es el país más grande de África por superficie? — A) Sudán · **B) Argelia** · C) RD del Congo · D) Libia
- ¿Cuál es el río más largo de Europa? — A) Danubio · B) Rin · C) Sena · **D) Volga**
- ¿Qué planeta tiene más lunas confirmadas? — A) Júpiter · B) Urano · **C) Saturno** · D) Neptuno
- ¿Quién fue la primera mujer en viajar al espacio? — A) Sally Ride · **B) Valentina Tereshkova** · C) Svetlana Savítskaya · D) Mae Jemison

_Reservas:_
- ¿Cuántos corazones tiene un pulpo? — A) 1 · B) 2 · **C) 3** · D) 5 (reserva)
- ¿Qué país tiene más islas en el mundo? — A) Indonesia · B) Filipinas · C) Canadá · **D) Suecia** (reserva)

## 5. Territorio enemigo (opciones, 2 pt, 20 s)
Comodines: llamada, **doble o nada** (antes "saltar"), cambiar, 50/50.

- ¿Cómo se llama el planeta natal de los saiyajin? — A) Namek · B) Planeta Cold · **C) Planeta Vegeta** · D) Planeta Yardrat
- ¿Con qué tipo de luz se secan las uñas semipermanentes en los salones? — **A) Luz UV** · B) Luz infrarroja · C) Luz blanca normal · D) Luz láser
- ¿Cómo se llama el padre de Goku? — **A) Bardock** · B) Raditz · C) Nappa · D) Turles
- ¿Qué producto se usa para tapar ojeras e imperfecciones? — A) Rubor · B) Iluminador · C) Contorno · **D) Corrector**
- ¿Quién derrota a Cell en los Juegos de Cell? — A) Goku · **B) Gohan** · C) Vegeta · D) Piccolo
- ¿Qué técnica de maquillaje esculpe el rostro con luces y sombras? — A) Strobing · B) Baking · **C) Contouring** · D) Draping
- ¿Cómo se llama el disco de energía cortante de Krilin? — A) Masenko · B) Makankosappo · C) Taiyoken · **D) Kienzan**
- ¿Cómo se llama la manicura de punta blanca? — **A) Francesa** · B) Rusa · C) Holográfica · D) Cat eye

_Reservas:_
- ¿Cómo se llama la fusión de Goku y Vegeta con las Pothalas? — A) Gogeta · **B) Vegetto** · C) Gotenks · D) Kefla (reserva)
- ¿Qué es un gloss? — **A) Brillo para los labios** · B) Tinte líquido duradero · C) Lápiz para perfilar labios · D) Bálsamo para labios secos (reserva)

## 6. Elige tu tema (abierta, 1 pt, 20 s)
Comodines: llamada, **doble o nada** (antes "saltar"), cambiar.

### Tema: Minecraft
- ¿Cuántos bloques de base necesita un faro de 4 niveles? → **164**  _(nota: 9 + 25 + 49 + 81 de pirámide. Contando el faro en sí son 165.)_
- ¿Qué ingredientes lleva el Cristal del End? → **Vidrio, ojo de Ender, lágrima Ghast**  _(nota: Receta: 7 vidrios (todo el cuadro), 1 ojo de Ender al centro y 1 lágrima de Ghast abajo al medio.)_
- ¿Cuántos ojos de Ender activan un portal al End vacío? → **12**  _(nota: El portal tiene 12 marcos.)_
- ¿Cuántos puntos de vida tiene el Ender Dragon? → **200 puntos de vida**  _(nota: Equivale a 100 corazones.)_

_Reservas:_ ¿Con qué dos ítems se craftea un ojo de Ender? → Perla de Ender y polvo de Blaze · ¿Cuántos bloques de obsidiana hacen falta como mínimo para un portal al Nether? → 10 · ¿Qué lleva una mesa de encantamientos? → 2 diamantes, 4 obsidiana y 1 libro

### Tema: Cine y series
- ¿Cómo se llama el restaurante de pollo que Gus Fring usa como fachada en Breaking Bad? → **Los Pollos Hermanos**
- ¿Qué canción de Kate Bush salva a Max en la cuarta temporada de Stranger Things? → **“Running Up That Hill”**
- ¿Cómo se llama el prometido de Rose, la protagonista de Titanic? → **Cal Hockley**
- ¿Cuál fue el primer largometraje totalmente animado por computadora (3D)? → **Toy Story (1995)**  _(nota: Es de Pixar y Disney. Técnicamente, el primer largometraje totalmente animado por computadora (CGI).)_

_Reservas:_ ¿Qué película se estrenó junto a Oppenheimer en 2023 y creó el “Barbenheimer”? → Barbie · ¿Cuál es el verdadero nombre del abogado Saul Goodman en Breaking Bad? → Jimmy McGill · ¿En qué ciudad ficticia de Indiana transcurre Stranger Things? → Hawkins

### Tema: Cultura y arte
- ¿Quién pintó La noche estrellada? → **Vincent van Gogh**
- ¿En qué ciudad ocurrió La Noche de los Lápices? → **La Plata**  _(nota: Fue el 16 de septiembre de 1976 (secuestro de estudiantes secundarios).)_
- ¿Qué civilización construyó Machu Picchu? → **Los incas**
- ¿Qué compositor, ya sordo, escribió la Novena Sinfonía? → **Ludwig van Beethoven**

_Reservas:_ ¿Quién escribió Cien años de soledad? → Gabriel García Márquez · ¿Qué artista pintó el Guernica? → Pablo Picasso · ¿Quién escribió Don Quijote de la Mancha? → Miguel de Cervantes

## 7. Matemáticas (abierta, 1 pt, 40 s · 60 s en la pregunta de la luz del Sol)
Responden **los dos** equipos a la vez, cada uno muestra su número, el conductor los carga y pulsa "Calcular ganador": **gana el más cercano**. Empate exacto: suman los dos. Empate a igual distancia: nadie. **Sin comodines.**

- ¿Cuánto es el 35% de 240? → **84**
- ¿Cuánto es 23 × 14? → **322**
- Resuelve: 4x − 9 = x + 15. ¿Cuánto vale x? → **x = 8**
- ¿Cuánto da la suma de todos los números del 1 al 100? → **5050**
- ¿Cuántos minutos tiene una semana? → **10.080**  _(nota: 7 × 24 × 60)_
- ¿Cuántos segundos tarda la luz del Sol en llegar a la Tierra? (aproximado) → **Unos 500 segundos**  _(nota: 8 min 20 s. Acepta entre 480 y 520. Esta pregunta tiene 60 s.)_
- ¿Cuántos días de clase tiene como mínimo el ciclo lectivo argentino según la ley? → **180**  _(nota: Ley 25.864. Dato extra: el Consejo Federal de Educación apunta a 190 días.)_

_Reservas:_
- ¿Cuánto es 15² − 14²? (sin calculadora) → **29**  _(nota: Truco: (15 + 14) × (15 − 14).)_ (reserva)
- ¿Cuánto es 2 elevado a la 12? → **4096** (reserva)
- ¿Cuánto es 18 × 15? → **270** (reserva)

## 8. Capciosas y lógica (abierta, 1 pt, 30 s · 60 s en la pregunta de los gatos)
Turno alternado como en las rondas normales y **sin rebote**: si el equipo falla, se revela y se sigue con la siguiente. Comodines: llamada, **doble o nada** (antes "saltar"), cambiar.
**Esta ronda NO tiene 50/50** (son preguntas abiertas).

- Un gallo pone un huevo en la punta de un techo: ¿hacia dónde cae? → **Ninguno, no ponen huevos**
- ¿Cuántos animales de cada especie llevó Moisés en el arca? → **Ninguno, fue Noé**
- Con un solo fósforo, una vela, una lámpara y una chimenea, ¿qué enciendes primero? → **El fósforo**
- Te dan 3 pastillas, una cada media hora. ¿Cuánto dura el tratamiento? → **1 hora**  _(nota: La primera se toma al inicio.)_
- Si 3 gatos cazan 3 ratones en 3 min, ¿cuántos gatos cazan 100 ratones en 100 min? → **3 gatos**  _(nota: Esta pregunta tiene 60 s.)_

_Reservas:_
- ¿Qué es lo que mientras más le quitas, más grande se hace? → **Un hoyo** (reserva)
- ¿Cuántos meses tienen 28 días? → **Todos** (reserva)

## 9. Gran final (abierta, 2 pt, 10 s, con rebote)
Empieza el que va perdiendo. Si acierta, **sigue el mismo equipo**; si falla, rebota al otro; si **fallan los dos**, la siguiente la vuelve a empezar el que la empezó.

- ¿Cuál es el océano más pequeño del mundo? → **Ártico**
- ¿Cuál es la capital de Canadá? → **Ottawa**
- ¿Cómo se dice "ardilla" en inglés? → **Squirrel**
- ¿Cuánto es 1000 dividido entre 8? → **125**
- ¿Cuál es el único metal que es líquido a temperatura ambiente? → **Mercurio**
- ¿Cuál es el país más poblado del mundo actualmente? → **India**  _(nota: Verificar antes de grabar: el dato puede cambiar.)_

## 10. Desempate (abierta, 1 pt, 10 s)

- ¿Cuántos lados tiene un dodecágono? → **12**
- ¿Cuál es la capital de Turquía? → **Ankara**
- ¿Cuánto es 13 × 13? → **169**
- Último recurso: nombra 5 países de África en 10 segundos. → **Gana el primero en completarlos**  _(nota: Gana el primero en completarlos.)_

## Notas de producción / OBS

- Reloj pausado durante el redoble; tic-tac en los últimos 10 s; campana al llegar a 0.
- Solo en la **final** (la única con rebote) se marca **Acierto/Error ANTES de revelar**: el programa avisa si el otro equipo queda con la pregunta por rebote. En el resto de las rondas se revela primero y recién ahí se marca.
- La **final** revela directo (sin redoble); el resto de las rondas suenan el redoble antes de mostrar la respuesta.
- Todos los sonidos salen por el **mismo dispositivo** de audio de Windows (redoble incluido).
- Recargar banco desde el programa si se edita el JSON. Recargar fuentes de OBS si se editan los HTML.
