#!/bin/bash

# Colores y emojis
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
CHECK="✅"
CROSS="❌"
INFO="ℹ️"
DOCKER="🐳"
MSG="💬"
FILE="📄"
BROADCAST="📢"

echo -e "${CYAN}${DOCKER} Link-Chat: Pruebas automáticas en Docker${NC}"

# Verificar permisos de Docker
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}${CROSS} No tienes permisos para usar Docker. Ejecuta el script con sudo o agrega tu usuario al grupo docker."
    echo -e "${YELLOW}Ejemplo: sudo ./test_docker.sh${NC}"
    exit 1
fi

# 0. Limpiar contenedores previos
for c in chat1 chat2; do
    if docker ps -a --format '{{.Names}}' | grep -w "$c" >/dev/null; then
        echo -e "${YELLOW}${INFO} Eliminando contenedor previo: $c"
        docker rm -f "$c" 2>/dev/null
    fi
done

# 1. Construir la imagen
echo -e "${INFO} Construyendo imagen Docker..."
if ! docker build -t link-chat .; then
    echo -e "${RED}${CROSS} Error al construir la imagen."
    echo -e "${YELLOW}Verifica que el Dockerfile exista y que tengas permisos de escritura en la carpeta.${NC}"
    read -p "¿Quieres intentar de nuevo? [y/N]: " retry
    [[ "$retry" =~ ^[yY]$ ]] && exec "$0" || exit 1
fi

# 2. Crear red bridge personalizada
echo -e "${INFO} Creando red bridge personalizada..."
docker network create --driver bridge linknet 2>/dev/null

# 3. Levantar dos contenedores en segundo plano
echo -e "${INFO} Levantando dos contenedores..."
if ! docker run --rm -d --cap-add=NET_RAW --network linknet --name chat1 link-chat tail -f /dev/null; then
    echo -e "${RED}${CROSS} Error al iniciar chat1. ¿La imagen se construyó correctamente?${NC}"
    exit 1
fi
if ! docker run --rm -d --cap-add=NET_RAW --network linknet --name chat2 link-chat tail -f /dev/null; then
    echo -e "${RED}${CROSS} Error al iniciar chat2. ¿La imagen se construyó correctamente?${NC}"
    docker stop chat1 2>/dev/null
    exit 1
fi

# 4. Obtener MAC de ambos contenedores
MAC1=$(docker exec chat1 cat /sys/class/net/eth0/address 2>/dev/null)
MAC2=$(docker exec chat2 cat /sys/class/net/eth0/address 2>/dev/null)
if [[ -z "$MAC1" || -z "$MAC2" ]]; then
    echo -e "${RED}${CROSS} No se pudo obtener la MAC de los contenedores. ¿El contenedor está corriendo y tiene eth0?"
    docker stop chat1 chat2 2>/dev/null
    docker network rm linknet 2>/dev/null
    exit 1
fi
echo -e "${GREEN}${CHECK} MAC chat1: $MAC1"
echo -e "${GREEN}${CHECK} MAC chat2: $MAC2"

# Función para pedir confirmación
confirm() {
    read -p "$(echo -e "${YELLOW}$1 [y/N]:${NC} ")" resp
    case "$resp" in
        [yY]*) return 0 ;;
        *) echo -e "${RED}Cancelado.${NC}"; return 1 ;;
    esac
}

# Menú interactivo
while true; do
    echo -e "\n${CYAN}¿Qué funcionalidad deseas probar?${NC}"
    echo -e "1) ${MSG} Enviar mensaje de chat1 a chat2"
    echo -e "2) ${FILE} Enviar archivo de chat2 a chat1"
    echo -e "3) ${BROADCAST} Enviar mensaje broadcast desde chat1"
    echo -e "4) ${INFO} Escanear hosts LAN desde chat1"
    echo -e "5) ${CROSS} Salir y limpiar"
    read -p "Elige una opción [1-5]: " opt

    case "$opt" in
        1)
            echo -e "${INFO} Vas a enviar un mensaje de chat1 a chat2 usando la MAC de chat2: $MAC2"
            confirm "¿Continuar?" || continue
            # Iniciar receptor en chat2 antes del envío
            docker exec chat2 python3 -m src.main recv_msg --timeout=10 &
            sleep 1
            if ! docker exec chat1 python3 -m src.main send_msg $MAC2 "Hola desde chat1!"; then
                echo -e "${RED}${CROSS} Error al enviar el mensaje. Revisa los logs del contenedor chat1.${NC}"
            else
                echo -e "${GREEN}${CHECK} Mensaje enviado."
            fi
            wait
            ;;
        2)
            echo -e "${INFO} Vas a enviar un archivo de chat2 a chat1 usando la MAC de chat1."
            confirm "¿Continuar?" || continue
            echo "Archivo de prueba" > testfile.txt
            docker cp testfile.txt chat2:/testfile.txt
            # Iniciar receptor en chat1 antes del envío
            docker exec chat1 python3 -m src.main recv_file /testfile_recibido.txt --timeout=10 &
            sleep 1
            if ! docker exec chat2 python3 -m src.main send_file $MAC1 /testfile.txt; then
                echo -e "${RED}${CROSS} Error al enviar el archivo. Revisa los logs del contenedor chat2.${NC}"
            else
                echo -e "${GREEN}${CHECK} Archivo enviado."
            fi
            wait
            echo -e "${INFO} Archivo recibido guardado como /testfile_recibido.txt en chat1."
            ;;
        3)
            echo -e "${INFO} Vas a enviar un mensaje broadcast desde chat1 a todos los hosts."
            confirm "¿Continuar?" || continue
            # Iniciar receptor en chat2 antes del broadcast
            docker exec chat2 python3 -m src.main recv_msg --timeout=10 &
            sleep 1
            if ! docker exec chat1 python3 -m src.main broadcast "Mensaje broadcast desde chat1!"; then
                echo -e "${RED}${CROSS} Error al enviar el mensaje broadcast.${NC}"
            else
                echo -e "${GREEN}${CHECK} Mensaje broadcast enviado."
            fi
            wait
            ;;
        4)
            echo -e "${INFO} Vas a escanear los hosts LAN desde chat1."
            confirm "¿Continuar?" || continue
            # Mostrar tabla ARP antes
            echo -e "${CYAN}Tabla ARP antes del escaneo:${NC}"
            docker exec chat1 arp -n
            # Verificar IP de chat2
            IP2=$(docker exec chat2 hostname -I | awk '{print $1}')
            if [[ -z "$IP2" ]]; then
                echo -e "${RED}${CROSS} No se pudo obtener la IP de chat2."
            else
                # Enviar mensaje directo para poblar ARP
                docker exec chat2 python3 -m src.main recv_msg --timeout=5 &
                sleep 1
                docker exec chat1 python3 -m src.main send_msg $MAC2 "Ping ARP para escaneo"
                wait
                # Hacer ping
                docker exec chat1 ping -c 1 $IP2 >/dev/null 2>&1
            fi
            # Mostrar tabla ARP después
            echo -e "${CYAN}Tabla ARP después del escaneo:${NC}"
            docker exec chat1 arp -n
            if ! docker exec chat1 python3 -m src.main scan; then
                echo -e "${RED}${CROSS} Error al escanear hosts LAN.${NC}"
            fi
            ;;
        5)
            echo -e "${INFO} Limpiando y saliendo..."
            docker stop chat1 chat2 2>/dev/null
            docker network rm linknet 2>/dev/null
            rm -f testfile.txt
            echo -e "${GREEN}${CHECK} Pruebas finalizadas.${NC}"
            break
            ;;
        *)
            echo -e "${RED}Opción no válida.${NC}"
            ;;
    esac
done