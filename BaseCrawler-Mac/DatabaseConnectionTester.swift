//
//  DatabaseConnectionTester.swift
//  BaseCrawler-Mac
//
//  Created by Christopher M. Clendening on 2/18/26.
//

import Foundation

// MARK: - Connection Test Result

enum ConnectionTestResult {
    case success
    case failure(ConnectionTestError)
    
    var isSuccess: Bool {
        if case .success = self {
            return true
        }
        return false
    }
    
    var errorMessage: String? {
        if case .failure(let error) = self {
            return error.localizedDescription
        }
        return nil
    }
}

// MARK: - Connection Test Error

enum ConnectionTestError: Error, LocalizedError {
    case invalidConfiguration(String)
    case connectionTimeout
    case authenticationFailed(String)
    case databaseNotFound(String)
    case networkError(String)
    case unsupportedDatabaseType
    case unknownError(String)
    
    var errorDescription: String? {
        switch self {
        case .invalidConfiguration(let msg):
            return "Invalid configuration: \(msg)"
        case .connectionTimeout:
            return "Connection timeout - could not reach database"
        case .authenticationFailed(let msg):
            return "Authentication failed: \(msg)"
        case .databaseNotFound(let msg):
            return "Database not found: \(msg)"
        case .networkError(let msg):
            return "Network error: \(msg)"
        case .unsupportedDatabaseType:
            return "This database type is not yet supported"
        case .unknownError(let msg):
            return "Unknown error: \(msg)"
        }
    }
}

// MARK: - Database Connection Tester Protocol

protocol DatabaseConnectionTester {
    /// Test if the database connection is valid and can authenticate
    func testConnection(
        host: String,
        port: Int,
        username: String,
        password: String,
        database: String,
        useSSL: Bool
    ) async -> ConnectionTestResult
    
    /// Quick check if the database port is reachable (fallback for unsupported types)
    func testReachability(host: String, port: Int) async -> ConnectionTestResult
}

// MARK: - Default Reachability Implementation

extension DatabaseConnectionTester {
    func testReachability(host: String, port: Int) async -> ConnectionTestResult {
        guard !host.isEmpty else {
            return .failure(.invalidConfiguration("Host cannot be empty"))
        }
        
        guard (1...65535).contains(port) else {
            return .failure(.invalidConfiguration("Port must be between 1 and 65535"))
        }
        
        return await withCheckedContinuation { continuation in
            var hints = addrinfo()
            hints.ai_socktype = SOCK_STREAM
            hints.ai_family = AF_UNSPEC
            
            var res: UnsafeMutablePointer<addrinfo>? = nil
            let portStr = String(port)
            
            guard getaddrinfo(host, portStr, &hints, &res) == 0, let addr = res else {
                continuation.resume(returning: .failure(.networkError("Could not resolve host: \(host)")))
                return
            }
            defer { freeaddrinfo(res) }
            
            let sock = socket(addr.pointee.ai_family, addr.pointee.ai_socktype, addr.pointee.ai_protocol)
            guard sock >= 0 else {
                continuation.resume(returning: .failure(.networkError("Could not create socket")))
                return
            }
            defer { close(sock) }
            
            // Set non-blocking
            _ = fcntl(sock, F_SETFL, O_NONBLOCK)
            
            connect(sock, addr.pointee.ai_addr, addr.pointee.ai_addrlen)
            
            var writeSet = fd_set()
            var errorSet = fd_set()
            __darwin_fd_set(sock, &writeSet)
            __darwin_fd_set(sock, &errorSet)
            
            var timeout = timeval(tv_sec: 5, tv_usec: 0)
            let ready = select(sock + 1, nil, &writeSet, &errorSet, &timeout)
            
            guard ready > 0 else {
                continuation.resume(returning: .failure(.connectionTimeout))
                return
            }
            
            // Check for socket-level error
            var sockErr: Int32 = 0
            var errLen = socklen_t(MemoryLayout<Int32>.size)
            getsockopt(sock, SOL_SOCKET, SO_ERROR, &sockErr, &errLen)
            
            if sockErr == 0 {
                continuation.resume(returning: .success)
            } else {
                continuation.resume(returning: .failure(.networkError("Connection failed with error code: \(sockErr)")))
            }
        }
    }
}
