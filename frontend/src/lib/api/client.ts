const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";


/**
 * API错误详情结构
 * field：出错的表单/请求体字段名（可选）
 * reason：该字段错误描述（可选）
 * [key: string]: unknown：允许附加任意其他额外字段，兼容后端扩展返回
 */
export interface ApiErrorDetail {
  field?: string;
  reason?: string;
  [key: string]: unknown;
}


export class ApiError extends Error {

    /**
     * @param status HTTP响应状态码，如400、401、404、500
     * @param code 后端业务错误码
     * @param message 错误提示文字
     * @param details 字段级别的详细错误数组，表单校验失败时会携带
     */
    constructor(
        public readonly status: number,
        public readonly code: string,
        message: string,
        public readonly details: ApiErrorDetail[] = [],
    ) {
        super(message);
        this.name = "ApiError";
    }
}


/**
 * 封装fetch的通用接口请求函数
 * 统一处理请求头、错误捕获、后端错误解析，返回泛型Promise
 * @template T 期望接口成功返回的数据类型
 * @param path 接口路径
 * @param options
 * @returns Promise<T> 成功时返回后端json数据
 * @throws {ApiError} HTTP状态非2xx时抛出ApiError自定义异常
 */
export async function apiRequest<T>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${path}`,{
        ...options,
        headers: {
            Accept: "application/json",
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers,
        },
    });

    if(!response.ok) {
        let body: {
            error?: {
                code?: string;
                message?: string;
                details?: ApiErrorDetail[];
            };
        } = {};

        try {
            body = await response.json();
        } catch {

        }

        throw new ApiError(
            response.status,
            body.error?.code?? "UNKNOWN_ERROR",
            body.error?.message ?? "请求失败",
            body.error?.details ?? [],    
        )
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return response.json() as Promise<T>;

}