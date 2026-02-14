# Grupo-Q 
# Marc Martínez Arias
# Pedro Barros Bobadilla
# URL: https://github.com/Code-Cram/PROGRAMACION_CONCURRENTE_Y_DISTRIBUIDA_Grupo_Q

"""
Vamos a desarrollar un programa que tiene que ser
concurrente y además usar 10 hilos para encontrar
todos los números primos del 1 al 100.000.

Para ello, vamos a definir primero que es la concurrencia
y que es un hilo para entender que vamos a hacer.

De forma resumida, para crer este programa vamos a dividirlo
en subprocesos (concurrencia). Estos subprocesos son los
hilos o threads, así  que al tener 100.000 números, lo 
inteligente sería dividirlo en 10 hilos y que cada hilo
se encargue de 10.000 números. 

Voy a intentar generar una función para  cualquier n
y lo voy a aplicar para el caso de 100.000 números.
"""

#Importamos las librerías necesarias
import math
import threading
import time

# Definimos la función que encuentra los primos
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
    # Los divisores de un número acaban a partir de la mitad de su valor. Es decir,
    # A partir de n/2 ya no hay divisores, así que hay que comprobar la mitad de números.
    """
    Descartamos esta condición debido a que utilizamos la raiz para comprobarlo
    half = n//2
    for i in range (2, half+1):
        if n % i == 0:
            return False
    """
    # Vamos a utilizar la raiz para comprobar si un número es primo.
    # Si no encontramos un divisor entre [2,sqrt(n)] entonces el número es primo.
    # Quitamos los pares y partimos de los casos base.
    lim_sup = int(math.sqrt(n))
    for i in range(7, lim_sup +1,2):
        if n % i == 0:
            return False
    
    return True

"""
Entonces, hemos creado una función que por cada número tiene que comprobar los
divisores del rango [2,sqrt(n)], si no se encuentra ninguno el número es primo.
Se descartan las propiedades básicas: pares, divisible entre 5 y 10. Suma de las 
cifras divisible entre 3. Esta función tiene un coste O(sqrt(n))

Ahora vamos a proceder a diseñar la función que va a trabajar con 10 hilos.
Va a recibir el número de dígitos que tiene que buscar, los hilos que va coger y
va a devolver la lista con los primos y el número de primos encontrados.
Además, la complejidad temporal de esta función es O(n*sqrt(n))

También vamos a crear una función suport para crear correctamente los hilos.
Vamos añadir también un temporizador para ver si es veloz.
"""

# Definimos la función que busca los primos
def search_primes(start:int,end:int,primes_list:list) -> None:
    # Esta función es lo que ejecutará cada hilo 
    for num in range(start, end + 1):
        if found_primes(num):
            primes_list.append(num)
            
# Ahora la función que separa la función en threads
def primes_threads (n:int,threads:int) -> (list,int,float):
    # Iniciamos temporizador
    start = time.time()
    # Definimos dos listas vacías y dividimos la cifra entre el número de hilos
    primos = []
    hilos = []
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
            target = search_primes,
            args = (inicio,fin,primos))
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


# Ejemplo resolviendo el problema inicial
print(found_primes(49)) # False
print(found_primes(71)) # True
print(primes_threads(100000,10))
