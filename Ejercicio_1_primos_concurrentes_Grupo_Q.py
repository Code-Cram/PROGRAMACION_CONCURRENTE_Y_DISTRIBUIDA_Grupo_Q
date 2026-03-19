# Grupo-Q 
# Marc Martínez Arias
# Pedro Barros Bobadilla
# URL: https://github.com/Code-Cram/PROGRAMACION_CONCURRENTE_Y_DISTRIBUIDA_Grupo_Q


"""
En este caso, tenemos que desarrollar una versión  del
antiguo ejercicio pero sin que le afecte el GIL.

En el antiguo ejercicio ya desarrollamos un programa que encontraba
los números primos con  hilos. Sin embargo, debido al GIL los hilos no
se ejeutaban a la vez, sino que iba de uno en uno. Esta vez vamos a intentar
que el GIL no interfiera y se ejecuten los 10 hilos a la vez, obteniendo
la forma óptima para encontrar los números primos correspondientes.

Para ello, vamos a utilizar el multiprocesamiento. Con esto conseguimos
que cada thread tenga memoria separada del resto de los threads y se ejecuten 
por separado. Entonces, si estamos conseguiendo una paralelización real. 
"""

# Importamos las librerías necesarias
import math
import time
import threading
import multiprocessing

# Importamos la función del ejercicio anterior de la misma forma
def found_primes(n:int) -> bool:
    # Primer número primo 2, todo valor menor que 2 no es primo.
    if n < 2:
        return False
    # Casos básicos
    if n == 2 or n == 3 or n == 5 or n == 7 or n == 11 or n==13:
        return True
    # Criterios de divisibilidad.
    # Todo número par, terminado en 5 o 0 no es primo.
    # Los terminados en 0 son pares.
    if n % 2 == 0:
        return False
    if n % 5 == 0: 
        return False
    # Todo número que la suma de sus cifras es divisible entre 3 no es primo.
    n_str = str(n)
    suma = 0
    for i in n_str:
        suma += int(i)
    if suma % 3 == 0:
        return False
    # Vamos a utilizar la raiz para comprobar si un número es primo.
    # Si no encontramos un divisor entre [2,sqrt(n)] entonces el número es primo.
    # Quitamos los pares y partimos de los casos base.
    lim_sup = int(math.sqrt(n))
    for i in range(7, lim_sup +1,2):
        if n % i == 0:
            return False
    
    return True

# Definimos la función que busca los primos para hilos
def search_primes_with_lock(start: int, end: int, primes_list: list, lock: threading.Lock) -> None:
    primos_locales = []
    # Busca primos con una sincronización gracias al cerrojo.
    for num in range(start, end + 1):
        if found_primes(num):
            primos_locales.append(num)
    
    with lock:
        primes_list.extend(primos_locales)

# Definimos la función que busca los primos para procesos
def search_primes_process(start: int, end: int, primes_list) -> None:
    # Busca primos para multiprocessing con Manager.list
    primos_locales = []
    for num in range(start, end + 1):
        if found_primes(num):
            primos_locales.append(num)

    primes_list.extend(primos_locales)


# Ahora la función que separa la función en threads
def primes_threads (n:int,threads:int) -> (list,int,float):
    # Iniciamos temporizador
    start = time.time()
    # Definimos dos listas vacías y dividimos la cifra entre el número de hilos
    primos = []
    hilos = []
    lock = threading.Lock() # Creamos el cerrojo
    numbers_threads = n // threads
    # Creamos el bucle donde se va a aplicar la función por hilo
    for i in range(threads):
        inicio = i*numbers_threads+1
        if i < threads-1:
            fin = (i+1) * numbers_threads
        else:
            fin = n
    # Creamos el hilo y aplicamos la función
        hilo = threading.Thread(
            target = search_primes_with_lock,
            args = (inicio,fin,primos,lock))
        hilos.append(hilo)
        hilo.start()
    # Una vez se aplica la función a todos los hilos los juntamos
    for hilo in hilos:
        hilo.join()
    # Terminamos el tiempo
    end = time.time()
    duracion = round((end-start),5)
    # Devolvemos la lista de los primos y el número de primos
    return primos, len(primos), duracion

            
# Ahora definimos la función que consigue evitar el GIL.
def primes_multiprocessing (n:int,n_procesos:int) -> (list,int,float):
    # Iniciamos temporizador
    start = time.time()
    # En vez de generar hilos creamos un manager que gestione los procesos
    manager = multiprocessing.Manager()
    primos = manager.list()
    procesos = []
    numeros_por_procesos = n //n_procesos # Para un millón serán 100000 si cogemos 10 hilos
    # Ahora vamos a crear el algoritmo
    for i in range(n_procesos):
        inicio = i*numeros_por_procesos+1
        if i < n_procesos-1:
            fin = (i+1) * numeros_por_procesos
        else:
            fin = n
    # En vez de un hilo creamos un proceso
        proceso = multiprocessing.Process(
            target=search_primes_process,
            args=(inicio, fin, primos)        
            )
        procesos.append(proceso)
        proceso.start()
    # Una vez se aplica la función a todos los n_procesos los juntamos
    for proceso in procesos:
        proceso.join()
    # Terminamos el tiempo
    end = time.time()
    duracion = round((end-start),5)
    # Devolvemos la lista de los primos y el número de primos
    primos_list = list(primos)
    return primos_list, len(primos), duracion

# Ejecutamos el ejemplo.
if __name__ == '__main__':
    print(found_primes(49))  # False
    print(found_primes(71))  # True
    
    resultado_mp, count_mp, time_mp = primes_multiprocessing(1_000_000, 10)
    print(f"Multiprocessing: {count_mp} primos en {time_mp}s")
    
    resultado_th, count_th, time_th = primes_threads(1_000_000, 10)
    print(f"Threads: {count_th} primos en {time_th}s")
    
# Podemos ver comparando los dos modelos que utilizando 
# multiprocesamiento se consiguen resultados 5 veces más rápido
