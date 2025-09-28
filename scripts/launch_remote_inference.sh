#!/bin/bash
# RC Car Remote Inference Launcher
# Makes it easy to start different components of the system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_usage() {
    echo "RC Car Remote Inference Launcher"
    echo "================================"
    echo ""
    echo "Usage: $0 <component> [options]"
    echo ""
    echo "Components:"
    echo "  server [--model MODEL_PATH] [--port PORT]"
    echo "    Start inference server on laptop (default: dummy model, port 8888)"
    echo ""
    echo "  client --server-ip IP [--port PORT]"
    echo "    Start remote client on Raspberry Pi"
    echo ""
    echo "  test-server [--port PORT]"
    echo "    Test laptop setup and dependencies"
    echo ""
    echo "  test-client --server-ip IP [--port PORT]" 
    echo "    Test Raspberry Pi setup and connectivity"
    echo ""
    echo "  setup-network [--mode MODE] [--server-ip IP]"
    echo "    Run network setup and testing utilities"
    echo ""
    echo "Examples:"
    echo "  # On laptop: start server with dummy model"
    echo "  $0 server"
    echo ""
    echo "  # On laptop: start server with trained model"
    echo "  $0 server --model ./trained_model.pth"
    echo ""
    echo "  # On Raspberry Pi: connect to laptop"
    echo "  $0 client --server-ip 192.168.1.100"
    echo ""
    echo "  # Test connectivity from Pi to laptop"
    echo "  $0 test-client --server-ip 192.168.1.100"
}

check_python_deps() {
    local component=$1
    echo "🔍 Checking Python dependencies for $component..."
    
    if [ "$component" = "server" ]; then
        python3 -c "import torch, torchvision, cv2, numpy; print('✅ Server dependencies OK')" 2>/dev/null || {
            echo "❌ Missing server dependencies. Install with:"
            echo "   pip install torch torchvision opencv-python numpy"
            exit 1
        }
    elif [ "$component" = "client" ]; then
        python3 -c "import cv2, numpy, serial; print('✅ Client dependencies OK')" 2>/dev/null || {
            echo "❌ Missing client dependencies. Install with:"
            echo "   pip install opencv-python numpy pyserial"
            exit 1
        }
    fi
}

start_server() {
    local model_path=""
    local port="8888"
    local dummy_model="--dummy-model"
    
    # Parse server arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model)
                model_path="$2"
                dummy_model=""
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            *)
                echo "Unknown server option: $1"
                exit 1
                ;;
        esac
    done
    
    check_python_deps "server"
    
    echo "🧠 Starting Remote Inference Server..."
    echo "Port: $port"
    if [ -n "$model_path" ]; then
        echo "Model: $model_path"
        cd "$PROJECT_ROOT"
        python3 src/network/remote_inference_server.py --port "$port" --model-path "$model_path"
    else
        echo "Model: Dummy (testing mode)"
        cd "$PROJECT_ROOT"
        python3 src/network/remote_inference_server.py --port "$port" $dummy_model
    fi
}

start_client() {
    local server_ip=""
    local port="8888"
    
    # Parse client arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server-ip)
                server_ip="$2"
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            *)
                echo "Unknown client option: $1"
                exit 1
                ;;
        esac
    done
    
    if [ -z "$server_ip" ]; then
        echo "❌ --server-ip required for client mode"
        exit 1
    fi
    
    check_python_deps "client"
    
    echo "🤖 Starting Remote Inference Client..."
    echo "Server: $server_ip:$port"
    cd "$PROJECT_ROOT"
    python3 src/network/remote_inference_client.py --server-ip "$server_ip" --server-port "$port"
}

test_server() {
    local port="8888"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                port="$2"
                shift 2
                ;;
            *)
                echo "Unknown test option: $1"
                exit 1
                ;;
        esac
    done
    
    echo "🧪 Testing Server Setup..."
    cd "$PROJECT_ROOT"
    python3 src/network/network_setup.py --mode server --port "$port"
}

test_client() {
    local server_ip=""
    local port="8888"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --server-ip)
                server_ip="$2"
                shift 2
                ;;
            --port)
                port="$2"
                shift 2
                ;;
            *)
                echo "Unknown test option: $1"
                exit 1
                ;;
        esac
    done
    
    if [ -z "$server_ip" ]; then
        echo "❌ --server-ip required for client test"
        exit 1
    fi
    
    echo "🧪 Testing Client Setup..."
    cd "$PROJECT_ROOT"
    python3 src/network/network_setup.py --mode client --server-ip "$server_ip" --port "$port"
}

run_network_setup() {
    cd "$PROJECT_ROOT"
    python3 src/network/network_setup.py "$@"
}

# Main command parsing
if [ $# -eq 0 ]; then
    print_usage
    exit 1
fi

case $1 in
    server)
        shift
        start_server "$@"
        ;;
    client)
        shift
        start_client "$@"
        ;;
    test-server)
        shift
        test_server "$@"
        ;;
    test-client)
        shift
        test_client "$@"
        ;;
    setup-network)
        shift
        run_network_setup "$@"
        ;;
    -h|--help)
        print_usage
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        print_usage
        exit 1
        ;;
esac